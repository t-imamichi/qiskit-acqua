# -*- coding: utf-8 -*-

# Copyright 2018 IBM.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""
The Deutsch-Jozsa algorithm.
"""

import logging
from qiskit_aqua.algorithms import QuantumAlgorithm
from qiskit_aqua import AquaError, PluggableType, get_pluggable_class
from qiskit import ClassicalRegister, QuantumCircuit 

logger = logging.getLogger(__name__)

class DeutschJozsa(QuantumAlgorithm):
    """The Deutsch-Jozsa algorithm."""
        
    CONFIGURATION = {
        'name': 'DeutschJozsa',
        'description': 'DeutschJozsa',
        'input_schema': {
            '$schema': 'http://json-schema.org/schema#',
            'id': 'dj_schema',
            'type': 'object',
            'properties': {
            },
            'additionalProperties': False
        },
        'problems': ['functionevaluation'],
        'depends': ['oracle'],
        'defaults': {
            'oracle': {
                'name': 'DeutschJozsaOracle'
            }
        }
    }

    def __init__(self, oracle):
        self.validate(locals())
        super().__init__()

        self._oracle = oracle
        self._circuit = None
        self._return = {}

    @classmethod
    def init_params(cls, params, algo_input):
        if algo_input is not None:
            raise AquaError("Unexpected Input instance.")

        dj_params = params.get(QuantumAlgorithm.SECTION_KEY_ALGORITHM)
 
        oracle_params = params.get(QuantumAlgorithm.SECTION_KEY_ORACLE)
        oracle = get_pluggable_class(PluggableType.ORACLE,
                                     oracle_params['name']).init_params(oracle_params)
        return cls(oracle)

    def construct_circuit(self):        
        if self._circuit is not None:
            return self._circuit
 
        # preoracle circuit
        qc_preoracle = QuantumCircuit(
            self._oracle.variable_register(),
            self._oracle.ancillary_register(),
        )
        qc_preoracle.h(self._oracle.variable_register())        
        qc_preoracle.x(self._oracle.ancillary_register())        
        qc_preoracle.h(self._oracle.ancillary_register())                
        qc_preoracle.barrier()
        
        # oracle circuit
        qc_oracle = self._oracle.construct_circuit()
        qc_oracle.barrier()

        # postoracle circuit
        qc_postoracle = QuantumCircuit(
            self._oracle.variable_register(),
            self._oracle.ancillary_register(),
        )
        qc_postoracle.h(self._oracle.variable_register())        
        qc_postoracle.barrier()

        # measurement circuit
        measurement_cr = ClassicalRegister(len(self._oracle.variable_register()), name='m')

        qc_measurement = QuantumCircuit(
            self._oracle.variable_register(),
            measurement_cr
        )
        qc_measurement.barrier(self._oracle.variable_register())
        qc_measurement.measure(self._oracle.variable_register(), measurement_cr)
        
        self._circuit = qc_preoracle + qc_oracle + qc_postoracle + qc_measurement
        return self._circuit
        
    def _run(self):
        qc = self.construct_circuit()
        
        self._return['circuit'] = qc
        self._return['measurements'] = self._quantum_instance.execute(qc).get_counts(qc)
        self._return['result'] = self._oracle.interpret_measurement(self._return['measurements'])
        self._return['oracle_evaluation'] = self._oracle.evaluate_classically(self._return['result'])
        
        return self._return