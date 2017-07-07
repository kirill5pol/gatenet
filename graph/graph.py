import tensorflow as tf
import numpy as np
#from parameters import Parameters
from tensorflow_utils import *

from graph.layer import *
from graph.sublayer import *
from graph.module import *

######################################################################
## Code for Graph construction
class Graph():

    def __init__(self, parameter_dict):
        self.input_layer = None
        self.gated_layers = None
        self.output_layer = None
        self.sublayers = None

        # Build new graph from param dict
        self.build_graph(parameter_dict)



    ## Build graph to test code
    def build_graph(self, parameter_dict):

        ## Define Hyperparameters #########################################################
        self.M = parameter_dict['M']
        self.L = parameter_dict['L']
        self.tensor_size = parameter_dict['tensor_size']
        self.gamma = parameter_dict['gamma']

        ## Define Sublayers ###############################################################
        self.sublayers = np.zeros(self.L + 1, dtype=object)
        input_size = self.tensor_size
        num_modules = self.M
        for i in range(self.L + 1):
            self.sublayers[i] = ConcatenationSublayerModule(input_size,num_modules)
        


        ## Define Modules #################################################################
        output_modules = np.zeros(1, dtype=object)
        output_modules[0] = LinearModule(weight_variable([self.sublayers[-1].output_size, 10]), 
                                         bias_variable([10]))
        ##################################################################################

        ## Define Layers #################################################################
        input_layer_defn = {'M': self.M,
                            'input_size': 784, 
                            'output_size': self.sublayers[0].input_size,
                            'module_type': PerceptronModule}
        self.input_layer = InputLayer(input_layer_defn)

        self.gated_layers = []
        for i in range(self.L):
            gated_layer_defn = {'M': self.M,
                                'input_size': self.sublayers[i].output_size, 
                                'output_size': self.sublayers[i+1].input_size,
                                'module_type': PerceptronModule}
            gated_layer = GatedLayer(gated_layer_defn, self.gamma)
            self.gated_layers.append(gated_layer)

        self.output_layer = OutputLayer(output_modules)


    ## Build graph to test code
    def return_logits(self, input_images):
        ## Construct graph ###############################
        layer_output = self.input_layer.process_layer(input_images)
        sublayer_output = self.sublayers[0].process_sublayer(layer_output)
        for i in range(self.L):
            layer_output = self.gated_layers[i].process_layer(sublayer_output)
            sublayer_output = self.sublayers[i+1].process_sublayer(layer_output)

        logits = self.output_layer.process_layer(sublayer_output)
        ##################################################
        return logits


    def determine_gates(self, image, x, sess):
        gates = np.zeros((self.L, self.M))
        for i in range(len(self.gated_layers)):
            g = sess.run([self.gated_layers[i].gates],
                         feed_dict={x:image})
            gates[i] = np.array(g)
        return gates
######################################################################





######################################################################
'''
    GRAPH API DOCUMENTATION:
        • Takes in:
            -  

    SUBLAYER API DOC:
        • Takes in:
            - Number of modules

    LAYER API DOCUMENTATION:
        • Takes in:
            - Input size
            - Layer definition (future: [M0 M1 M3 ... Mn])
                - Number of modules
                - Type of module (only use one type for now)
            - Sublayer Types (future is several)







































''' 
