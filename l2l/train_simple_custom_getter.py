from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import tensorflow as tf
from graph.graph import Graph
from graph.module import *
from graph.sublayer import *
from l2l.metaoptimizer import *
from tensorflow_utils import variable_summaries


# A simple (deterministic) 1D problem
def simple_problem(batch_size):
    x = np.random.rand(batch_size, 1) * 5
    y = np.sqrt(x)
    return (x, y)

class MLP():
    def __init__(self,
                 x,
                 y_,
                 hidden_sizes=[2,2], 
                 scope = 'init_graph',
                 activation=tf.nn.relu):

        _, b = x.get_shape().as_list()
        _, d = y_.get_shape().as_list()
        init_w = tf.contrib.layers.xavier_initializer(uniform=True, seed=1, dtype=tf.float32)
        init_b = tf.constant_initializer(0.1)

        self.scope = scope
        self.hidden_sizes = hidden_sizes
        self.input_size  = b
        self.output_size = d
        self.act = activation

        with tf.variable_scope(self.scope):
            ws = []
            bs = []
            prev_hidden = self.input_size
            # Hidden layers
            for i, hidden_size in enumerate(hidden_sizes):
                with tf.variable_scope('layer'+str(i)):
                    w = tf.get_variable('w'+str(i),[prev_hidden, hidden_size], initializer=init_w)
                    b = tf.get_variable('b'+str(i), [hidden_size], initializer=init_b)
                    ws.append(w)
                    bs.append(b)
                    prev_hidden = hidden_size

            # Ouput layer
            with tf.variable_scope('layer_out'):
                w = tf.get_variable('w_out', [prev_hidden, self.output_size], initializer=init_w)
                b = tf.get_variable('b_out', [self.output_size], initializer=init_b)
                ws.append(w)
                bs.append(b)
    def run(self, x, custom_getter=None):
        # Get the variables
        with tf.variable_scope(self.scope, reuse=True):
            ws = []
            bs = []
            # Hidden layers
            for i, hidden_size in enumerate(self.hidden_sizes):
                with tf.variable_scope('layer'+str(i)):
                    w = tf.get_variable('w'+str(i), custom_getter=custom_getter)
                    b = tf.get_variable('b'+str(i), custom_getter=custom_getter)
                    ws.append(w)
                    bs.append(b)
            # Ouput layer
            with tf.variable_scope('layer_out'):
                w = tf.get_variable('w_out', custom_getter=custom_getter)
                b = tf.get_variable('b_out', custom_getter=custom_getter)
                ws.append(w)
                bs.append(b)

        # Save the summaries
        with tf.name_scope('mlp_run_summaries'):
            for i, (w, b) in enumerate(zip(ws, bs)):
                variable_summaries(w, name='w_'+str(i))
                variable_summaries(b, name='b_'+str(i))

        # Run the graph with weights ws and biases bs 
        with tf.name_scope('run_graph'):
            # Process the layers
            prev_out = x
            # Process hidden layers
            for i, (w, b) in enumerate(zip(ws[:-1], bs[:-1])):
                with tf.variable_scope('layer'+str(i)):
                    prev_out = self.act(tf.matmul(prev_out, w)) + b
            # Process output layer
            with tf.variable_scope('layer_out'):
                return self.act(tf.matmul(prev_out, ws[-1])) + bs[-1]


################################################################################
######                        MAIN PROGRAM                                ######
################################################################################
def train(parameter_dict):
    with tf.Session() as sess:

        # Input placeholders
        x = tf.placeholder(tf.float32, [None, 1], name='x-input')
        y_ = tf.placeholder(tf.float32, [None, 1], name='y-input')

        ########## Define simple graph #########################################
        graph = MLP(x, y_)

        ########## Build the rest of the functions in the graph ################
        def loss_func(x=x, y_=y_, fx=graph.run, custom_getter=None):
            def build():
                y = fx(x, custom_getter=custom_getter)
                with tf.name_scope('loss'):
                    return tf.reduce_mean(tf.abs(y_ - y))
            return build

        # Get layer wise variable sharing for the meta optimizer
        shared_scopes = ['']

        # Meta optimization
        optimizer = MetaOptimizer(shared_scopes, name='MetaOptSimple')
        train_step = optimizer.minimize(loss_func=loss_func)
        ###optimizer = tf.train.AdamOptimizer(0.001)
        ###train_step = optimizer.minimize(loss)

        # Get the y, loss, and accuracy to use in printing out stuff later
        y = graph.run(x)

        with tf.name_scope('loss'):
            loss = loss_func()()
            tf.summary.scalar('loss', loss)
        with tf.name_scope('accuracy'):
            accuracy = tf.reduce_mean((y_ - y) / y_)
            tf.summary.scalar('accuracy', accuracy)

        merged = tf.summary.merge_all()
        writer = tf.summary.FileWriter('./logs/simple', graph=sess.graph)
        # Command to run: tensorboard --logdir=l2l/logs/simple

        # Initialize Variables
        tf.global_variables_initializer().run()

        ################ Run the graph #########################################
        for i in range(parameter_dict['num_batches']):
            tr_data, tr_label = simple_problem(parameter_dict['batch_size'])

            # Save summaries and print
            if i % parameter_dict['print_every'] == 0:
                summary, acc, _, predicted, loss_ = sess.run(
                                        [merged, accuracy, train_step, y, loss], 
                                        feed_dict={x: tr_data, y_: tr_label})

                # Write out summary at current time_step
                writer.add_summary(summary, i)

                # Print stuff out
                print('\nIteration: {}, accuracy: {}, loss: {}'.format(i, acc, loss))
                print('Predictions & Answers')
                for i in range(min(len(tr_label), 10)):
                    print('Pred: {}, Actual: {} -- Input: {}'.format(predicted[i], tr_label[i], tr_data[i]))

            else:
                acc, _, predicted, loss_ = sess.run(
                                        [accuracy, train_step, y, loss], 
                                        feed_dict={x: tr_data, y_: tr_label})



if __name__ == "__main__":

    parameter_dict = {
        'C': 1,
        'sublayer_type': AdditionSublayerModule,
        'hidden_size': 10,
        'gamma': 0,
        'batch_size': 20,
        'num_batches': 11,
        'learning_rate': 0.001,
        'print_every': 10,
        'M': 1,
        'L': 2,
        'module_type': PerceptronModule,
    }

    train(parameter_dict)