#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
holovqa v0.1
holographic MPS variational quantum algorithms 


Created on Mon Oct  5 09:58:45 2020
@author: acpotter
"""
#%% imports
import numpy as np
import cirq
import sympy 

#%% 
class IsoTensor(object):
    """
        node of an isometric tensor-network, generated by parameterized cirq unitary
        works equally for tensor network state (TNS) or operator (TNO); 
        for TNS: physical register implicitly assumed to start from reference state: |00..0> 
        
        Intention: circuit object intended to be easily adaptable to work equally with cirq, qiskit, etc...
    """
    def __init__(self,qubits,n_params,circuit_format = 'cirq'):
        """
        creates isometric tensor site for list of bond-register sizes
        intputs:
            qubits, list of qubit-registers, object-type depends on circuit_format (e.g. cirq, qiskit, etc...)
                note:
                    number of outgoing legs is automatically the same as incoming ones
                    0th leg denotes the physical leg, 
                    j>1 entries are (incoming) bond-legs
            n_params, int, number of parameters in circuit
            circuit_format, optional (default = 'cirq'), specifies which circuit 
                construction package to use for circuits
        """
        self.n_params = n_params
        self.circuit_format = circuit_format
        self.regdims = len(qubits)
        self.qubits = qubits
        self.tensor_shape = np.append(2**np.array(self.regdims),2**np.array(self.regdims))
        
        if circuit_format == 'cirq':
            ## setup circuit(s) ##
            self.param_names = [sympy.Symbol('x'+str(j)) for j in range(n_params)]
            self.circuit  = cirq.Circuit()
        else:
            raise NotImplementedError('Only cirq implemented')

    def unitary(self,params):
        """
        calls circuit simulator to construct unitary
        returns in shape specified by regdims
        inputs:
            - params, list or np.array of floats, circuit parameters
        """
        if self.circuit_format == 'cirq':            
            u = self.unitary_cirq(params)
        else:
            raise NotImplementedError('Only cirq implemented')
        return u
    
    def unitary_cirq(self,params):
        """ unitary constructor for cirq-based circuits """
        param_dict = dict(zip(self.param_names,params)) # create dictionary of parameters
        qubit_order = [q for qreg in self.qubits for q in qreg] # order to return the qubit unitary
        # resolve the symbolic circuit parameters to numerical values
        resolver = cirq.ParamResolver(param_dict)
        resolved_circuit = cirq.resolve_parameters(self.circuit, resolver)   
        u = resolved_circuit.unitary(qubit_order = qubit_order)
        return u.reshape(self.tensor_shape) # reshape as a multi-leg tensor

#%%
class HoloMPS(object):
    """
    Object for: Holographic MPS generated by variational/parameterized circuit 
    """
    
    
    def __init__(self,nphys,nbond,param_names,l_uc=1,circuit_format = 'cirq'):
        """
        inputs:
            nphys, int, number of physical qubits
            nbond, int, number of bond qubits
            l_uc, int, number of sites in unit cell
            param_names,list of sympy symbols, parameterized gate parameters (shared by all tensors)
            circuit_format, str, (default='cirq'), type of circuit editor/simulator used
        """
        self.nphys = nphys # number of physical qubits
        self.nbond = nbond # number of bond qubits
        self.l_uc = l_uc # length of unit cell
        self.param_names = param_names # list of sympy symbols (shared by all tensors)
        self.n_params = len(param_names)
        
        if circuit_format != 'cirq':
            self.qp = [cirq.NamedQubit('p'+str(j)) for j in range(nphys)] # physical qubits
            self.qb = [cirq.NamedQubit('b'+str(j)) for j in range(nbond)] # bond qubits
            self.qubits = [qp,qb]

            # make the MPS/tensor-train -- same qubits used by each tensor
            self.bdry_tensor = IsoTensor(qubits,self.n_params) # tensor for left boundary vector
            self.tensors = [IsoTensor(qubits,self.n_params) for j in range(l_uc)]

        else:
            raise NotImplementedError('Only cirq implemented')
        
    def compute_unitaries(self,params):
        """
        inputs:
            params, nested list of parameter values
        """
        # 
        self.ubdry = self.bdry_tensor.unitary(params) # boundary circuit tensor 
        self.ulist = [tensor.unitary(params) for tensor in self.tensors]
        return self.ubdry, self.ulist
    
    
    def mpo_expect(self,mpo):
        """
        inputs: 
            - mpo, list of np.arrays, 
                mpo tensors with indices ordered: physical,bond,physical,bond
                required: mpo has same unit cell as mps
        outputs:
            - expval <\psi|mpo|\psi>
        """
        
        raise NotImplementedError
#%% 
#def t_matrix(node_ket,node_bra,mpo):
#    """
#    computes transfer matrix for: <mps_ket|mpo|mps_bra>
#    inputs:
#        mps_bra = 
#    """
        
            
#%%
#class HoloMPS(object):
#    """
#    Object for: Holographic MPS generated by variational/parameterized circuit 
#    """
#    
#    def __init__(self,d,chi,l_uc=1,quantum_unit='qubit'):
#        """
#        inputs:
#            d, int, on-site physical dimension
#            chi, int, bond dimension
#            l_uc, int, length of unit cell (either iMPS or finite length MPS)
#            architecture, str, type of quantum units ('qubit', 'cQED', etc...)
#        """
#        if quantum_unit == 'qubit':
#            if np.mod(np.log2(d),1)!=0: 
#                raise ValueError('d must be a power of 2 for qubits')
#            if np.mod(np.log2(chi),1)!=0: 
#                raise ValueError('chi must be a power of 2 for qubits')
#
#            self.p=np.int(np.log2(d))
#            self.b=np.int(np.log2(chi))
#            self.l_uc = l_uc
#            
#            ## setup circuit(s) ##
#            # physical and bond qubit registers
#            self.qp = [cirq.NamedQubit('p'+str(j)) for j in range(self.p)]
#            self.qb = [cirq.NamedQubit('b'+str(j)) for j in range(self.b)]
#
#            # boundary-condition circuit (bond-only), sets left-BC's
#            self.bc_circuit = cirq.Circuit() 
#            # list of circuits (can be different for each site in unit cell
#            self.circuits = [cirq.Circuit() for j in range(self.l_uc)]
#        else:
#            raise NotImplementedError('quantum unit type {}'.format(quantum_unit))
#            
#    def set_circuits(self,circ_list:list,
#                     param_names:list,
#                     param_vals = None,
#                     bc_circ = None):
#        """
#        inputs:
#            circ_list, list of tuples cirq.Circuit(), len = l_uc
#            param_list, nested list of len l_uc, with entries = list of parameter names for site as sympy symbols
#            param_vals (optional), list (entry for each site) of dictionaries of parameter values, format = {param_name: param_value}, if None (default), initialize to all 0
#            bc_circ (optional), cirq.Circuit(), initializes bond-qubits, if None (default) start from all 0's
#        """
#        self.circuits = circ_list
#        self.param_names = param_names
#        if param_vals != None:
#            self.param_vals = param_vals
#        else: # default to all 0's
#            self.param_vals = [dict(zip(param_names[j],
#                                        [0.0 for k in range(len(param_names[j]))]
#                                        )) for j in range(self.l_uc)]
#        
#    #def unitaries(self,
#    
#    #def resolve_params

#%% test/debug
nphys = 1
nbond = 1
n_params = 2
qp = [cirq.NamedQubit('p'+str(j)) for j in range(nphys)] # physical qubits
qb = [cirq.NamedQubit('b'+str(j)) for j in range(nbond)] # bond qubits
qubits = [qp,qb]

node = IsoTensor(qubits, n_params)
circ = node.circuit
qs = node.qubits
symbols = node.param_names
for j in range(len(regdims)):
    for k in range(regdims[j]):
        circ.append(cirq.rx(symbols[0])(qs[j][k]))
        circ.append(cirq.rz(symbols[1])(qs[j][k]))
print(node.circuit)

u = node.unitary([0.0,np.pi])
print(u)


