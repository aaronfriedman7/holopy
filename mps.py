#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  6 11:05:06 2020

@author: acpotter
"""

import numpy as np
import scipy.linalg as la

#%% MPS class
class MPS(object):
    """
        matrix-product states
    
        Note/To-do:
        some of the code now assumes chi_in = chi_out, not necessarily the case
        e.g. TEBD/DMRG calculations will make bond dimension higher in middle of chain!
        however, this is ok for mpos generated by unitaries
    """
    
    def __init__(self,tensors,L=np.inf,bdry_vecs=[None,None], rcf = True):
        """
        inputs:
            L, int, length = # of repetitions of unit cell (default=np.inf = iMPS)
            tensors = list of bulk tensors as rank-3 np.arrays 
                index order: site, physical, bond-out, bond-in 
                ("in/out" refer to right canonical form ordering)
            self.bdry_vecs = list of [left-boundary, right-boundary]
                defaults = [None, None] will give left boundary = |0>, 
                right boundary traced over (as appropriate for holographic/sequential computations)
            rcf, bool, whether MPS is in right-canonical form 
                (default = True) b/c expect MPSs to come from unitary circuits as default
        """
        self.l_uc = len(tensors) # length of unit-cell
        self.L = L # number of repeating unit cells
        self.tensors = tensors
        # tensor dimensions
        self.d = tensors[0][:,0,0].size
        self.chi = tensors[0][0,:,0].size
        
        self.bdry_vecs = []
        # left boundary vector
        if np.array(bdry_vecs[0]==None).all():
            # if bdry_vec not specified, set to (1,0,0,0...)
            self.bdry_vecs += [np.zeros(self.chi)]
            self.bdry_vec[0][0]=1
        else:
            if bdry_vecs[0].size != self.chi:
                raise ValueError('left boundary vector different size than bulk tensors')
            self.bdry_vecs += [bdry_vecs[0]]
        
        # right boundary vector
        if np.array(bdry_vecs[1]==None).all():
            self.bdry_vecs += [None]
        else:
            if bdry_vecs[1].size != self.chi:
                raise ValueError('right boundary vector different size than bulk tensors')

            self.bdry_vecs += [bdry_vecs[1]]
    
    def transfer_matrix(self,mpo=None):
        """
        computes transfer matrix for the unit cell 
        (possibly sandwiching some specified mpo w/ the same unit cell size
        inputs:
            mpo, mpo-object, with same unit cell as self and same physical dimension
        ouputs:
            t_mat, np.array, transfer matrix for the unit cell
        """
        if mpo==None: # just transfer matrix for the wave-function
            # transfer matrix for each site
            t_mat_site = np.zeros([self.chi**2,self.chi**2],dtype=complex)
            # total transfer matrix for the unit-cell
            t_mat = np.eye(self.chi**2,self.chi**2,dtype=complex) 
            
            for j in range(self.l_uc): # loop through each site
                # compute t-matrix for that site
                t_tensor =  np.tensordot(
                                self.tensors[j].conj(),
                                self.tensors[j],
                                axes = ([0],[0]))
                # reorder axes and reshape into matrix
                t_mat_site = np.swapaxes(t_tensor,1,2).reshape(self.chi**2,self.chi**2)                
                # accumulate t-mat for unit cell
                t_mat = t_mat_site @ t_mat 
        else:
            chi_mpo = mpo.chi
            t_mat_site = np.zeros([self.chi**2 * chi_mpo,self.chi**2 * chi_mpo])
            t_mat = np.eye(self.chi**2*chi_mpo,self.chi**2*chi_mpo,dtype=complex) 
            for j in range(self.l_uc):
                chi_1 = mpo.chi * self.chi
                # contract mpo site-tensor with ket:
                mpo_on_ket = np.tensordot(mpo.tensors[j],self.tensors[j],axes=([2],[0]))
                mpo_on_ket_reshape = np.swapaxes(mpo_on_ket,2,3).reshape(self.d,chi_1,chi_1)

                # contract result with bra:
                chi_t = chi_1 * self.chi # total bond-dimension
                t_mat_site = np.swapaxes(
                        np.tensordot(self.tensors[j].conj(),mpo_on_ket_reshape,axes = ([0],[0])),
                        1,2).reshape(chi_t,chi_t)
                t_mat = t_mat_site @ t_mat # accumulate t-mat for unit cell
        return t_mat
    
    def expect(self,mpo=None):
        """
        computes <mps|mpo|mps> with left bc's set by bdry_vec
        and right bc's averaged over, as occurs in holographic simulations
        inputs: 
            mpo, mpo object w/ same unit cell and physical dimension
                default = None, in which case just returns <\psi|\psi>
        outputs:
            expect_val = complex, <psi|mpo|psi>
        """
        if self.L < np.inf:
            # finite length chain
            t_mat = np.linalg.matrix_power(self.transfer_matrix(mpo),self.L)
        
            if mpo == None: # no MPO inserted
                bvec_l = np.kron(self.bdry_vecs[0].conj(),self.bdry_vecs[0])
                if np.array(self.bdry_vecs[1]==None).all():
                    # right bc not specified -- sum over right vecs
                    t_mat_on_rvec = (t_mat @ bvec_l).reshape(self.chi**2)
                    rvec = np.eye(self.chi).reshape(self.chi**2)
                    expect_val = np.dot(rvec, t_mat_on_rvec)
                else:
                    bvec_r = np.kron(self.bdry_vecs[1].conj(),self.bdry_vecs[1])
                    expect_val = bvec_r.conj().T @ t_mat @ bvec_l
                    
            else: # mpo inserted
                bvec_l = np.kron(self.bdry_vecs[0].conj(),
                                 np.kron(mpo.bdry_vecs[0],self.bdry_vecs[0]))
                if np.array(self.bdry_vecs[1]==None).all():
                    # right bc not specified, 
                    # default = sum over all possible RBC's on the MPS-bond qubits
                    # use the specified right-boundary vector of the mpo
                    
                    # t-matrix acting on left vector
                    t_vleft = (t_mat @ bvec_l).reshape(self.chi,mpo.chi,self.chi)
                    mpo_rvec_contracted = np.tensordot(mpo.bdry_vecs[1],
                                               t_vleft,
                                               axes = ([0],[1])).reshape(self.chi**2)
                    rvec = np.eye(self.chi).reshape(self.chi**2)
                    expect_val = np.dot(rvec,mpo_rvec_contracted)
                else:
                    bvec_r = np.kron(self.bdry_vecs[1].conj(),
                                     np.kron(mpo.bdry_vecs[1],self.bdry_vecs[1]))
                    expect_val = bvec_r.conj().T @ t_mat @ bvec_l
            
        else:
            # do iMPS calculation
            #if self.rcf != True:
            #    self.convert_rcf()
            #
            #vals,vecs = la.eig(self.transfer_matrix(mpo))
            raise NotImplementedError
       
            

        return expect_val
    
    ## canonical form functions ##
    def check_rcf(self):
        """
        checks whether tensors are in right-canonical form (rcf)
        sets self.rcf to true or false accordingly
        """
        raise NotImplementedError
    
    def convert_rcf(self):
        """
        convert tensors into right-canonical form
        """
        raise NotImplementedError

#%%        
class MPO(object):
    """
    matrix product operator
    tensor index ordering: physical out, bond out, physical in, bond in
    """
    
    def __init__(self,tensors,L=np.inf,bdry_vecs=[None,None]):
        """
        inputs:
            l_uc, int, unit cell length
            L, int, length = # of repetitions of unit cell (default=-1 for MPS)
            tensors = list of bulk tensors as rank-4 np.arrays 
                index order: site, physical-out, bond-out, physical-in, bond-in 
                ("in/out" refer to right canonical form ordering)
            self.bdry_vecs = list of [left-boundary, right-boundary]
                defaults = [None, None] will give left & right boundary vecs = |0>, 
            rcf, bool, whether MPS is in right-canonical form 
                (default = True) b/c expect MPSs to come from unitary circuits as default
        """
        self.l_uc = len(tensors)
        self.L = L
        self.tensors = tensors
        # tensor dimensions
        self.d = tensors[0][:,0,0,0].size # physical leg dimension
        self.chi = tensors[0][0,0,:,0].size # bond leg dimension
        
        self.bdry_vecs = []
        # setup boundary vectors
        for j in range(2):
            if np.array(bdry_vecs[j]==None).all():
                # if bdry_vec not specified, set to (1,0,0,0...)
                self.bdry_vecs += np.zeros(self.chi)
                self.bdry_vecs[j]=1
            else:
                if bdry_vecs[j].size != self.chi:
                    raise ValueError('left boundary vector different size than bulk tensors')
                self.bdry_vecs += [bdry_vecs[j]]
        

#%% debug/test
#
#u_swap = np.array([[1,0,0,0],
#                   [0,0,1,0],
#                   [0,1,0,0],
#                   [0,0,0,1]]).reshape([2,2,2,2])
#
## ancilla controlled not    
#u_cx = np.array([[1,0,0,0],
#                 [0,0,0,1],
#                 [0,0,1,0],
#                 [0,1,0,0]]).reshape([2,2,2,2])
#
## random unitary    
#h_random = np.random.randn(4,4)
#h_random += h_random.T
#u_random = la.expm(-1j*h_random).reshape([2,2,2,2])
#    
## mps     
#l_uc = 1
#L = 1
#lvec = np.array([1,0])
#rvec = None#np.array([1,0]).T
#bdry_vecs = [lvec,rvec]
#tensors = np.array([u_random[:,:,0,:] for j in range(l_uc)])
#
#state = MPS(tensors,L=L,bdry_vecs=bdry_vecs) 
#t_mat = state.transfer_matrix()
#print('<psi|psi> = {}'.format(state.expect()))
#
## mpo test
#op_lvec = np.array([1,0])
#op_rvec = np.array([1,0]).T
#op_bdry_vecs = [op_lvec,op_rvec]
#op_tensors = np.array([u_swap for j in range(l_uc)])
#op = MPO(op_tensors,L=L,bdry_vecs=op_bdry_vecs)
#
#print('<psi|op|psi> = {}'.format(state.expect(op)))
