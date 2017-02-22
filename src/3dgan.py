#!/usr/bin/env python

__author__ = "Meet Shah"
__license__ = "MIT"

import os

import numpy as np
import tensorflow as tf
from tqdm import *

from utils import *

'''
Global Parameters
'''
n_epochs   = 20000
batch_size = 100
g_lr       = 0.0025
d_lr       = 0.00001
beta       = 0.5
alpha_d    = 5
alpha_g    = 0.0001
d_thresh   = 0.8 
strides    = [1,2,2,2,1]

def generator(z, batch_size=batch_size, phase_train=True, reuse=False):
 
    g_1 = tf.add(tf.matmul(z, weights['wg1']), biases['bg1'])
    g_1 = tf.reshape(g_1, [-1,4,4,4,512])
    g_1 = batchNorm(g_1, 512, phase_train)

    g_2 = tf.nn.conv3d_transpose(g_1, weights['wg2'], output_shape=[batch_size,8,8,8,256], strides=strides, padding="SAME")
    g_2 = tf.nn.bias_add(g_2, biases['bg2'])
    g_2 = batchNorm(g_2, 256, phase_train)
    g_2 = tf.nn.relu(g_2)

    g_3 = tf.nn.conv3d_transpose(g_2, weights['wg3'], output_shape=[batch_size,16,16,16,128], strides=strides, padding="SAME")
    g_3 = tf.nn.bias_add(g_3, biases['bg3'])
    g_3 = batchNorm(g_3, 128, phase_train)
    g_3 = tf.nn.relu(g_3)
    
    g_4 = tf.nn.conv3d_transpose(g_3, weights['wg4'], output_shape=[batch_size,32,32,32,1], strides=strides, padding="SAME")
    g_4 = tf.nn.bias_add(g_4, biases['bg4'])                                   
    g_4 = tf.nn.sigmoid(g_4)
    
    return g_4


def discriminator(inputs, batch_size=batch_size, is_train=True, reuse=False):

    d_1 = tf.nn.conv3d(inputs, weights['wd1'], strides=strides, padding="SAME")
    d_1 = tf.nn.bias_add(d_1, biases['bd1'])                               
    d_1 = tf.nn.relu(d_1)

    d_2 = tf.nn.conv3d(d_1, weights['wd2'], strides=strides, padding="SAME") 
    d_2 = tf.nn.bias_add(d_2, biases['bd2'])                                  
    d_2 = batchNorm(d_2, 128, phase_train)
    d_2 = tf.nn.relu(d_2)
    
    d_3 = tf.nn.conv3d(d_2, weights['wd3'], strides=strides, padding="SAME") 
    d_3 = tf.nn.bias_add(d_3, biases['bd3'])                                  
    d_3 = batchNorm(d_3, 128, phase_train)
    d_3 = tf.nn.relu(d_3) 

    d_4 = tf.nn.conv3d(d_3, weights['wd4'], strides=strides, padding="SAME")     
    d_4 = tf.nn.bias_add(d_4, biases['bd4'])                              
    d_4 = batchNorm(d_4, 128, phase_train)
    d_4 = tf.nn.relu(d_4) 

    shape = d_4.get_shape().as_list()
    dim = numpy.prod(shape[1:])
    d_5 = tf.reshape(d_4, shape=[-1, dim])
    d_5 = tf.add(tf.matmul(z, weights['wg1']), biases['bd5'])
    
    return d_5

def trainGAN():
    # size of initial noise vector that will be used for generator
    z_size = 100 

    initializer = tf.truncated_normal_initializer(stddev=0.02)

    z_vector = tf.placeholder(shape=[batch_size,z_size],dtype=tf.float32) 
    x_vector = tf.placeholder(shape=[batch_size,32,32,32,1],dtype=tf.float32) 

    # ---- DCGAN ----
    net_g_train = generator(z_vector, is_train=True, reuse=False) # generated mini-batch of 3d models from noisy z vectors 

    d_output_x = discriminator(x_vector, is_train=True, reuse=False) # probabilities for real 3d models
    d_output_x = tf.maximum(tf.minimum(d_output_x, 0.99), 0.01) # avoid inf and -inf
    summary_d_x_hist = tf.histogram_summary("d_prob_x", d_output_x)

    d_output_z = discriminator(net_g_train, is_train=True, reuse=True) # probabilities for generated 3d models
    d_output_z = tf.maximum(tf.minimum(d_output_z, 0.99), 0.01) # avoid inf and -inf
    summary_d_z_hist = tf.histogram_summary("d_prob_z", d_output_z)

    d_loss = -tf.reduce_mean(tf.log(d_output_x) + tf.log(1-d_output_z)) # loss for discriminator
    summary_d_loss = tf.scalar_summary("d_loss", d_loss)
    
    g_loss = -tf.reduce_mean(tf.log(d_output_z)) # loss for generator
    summary_g_loss = tf.scalar_summary("g_loss", g_loss)

    # the following parameter indices may change if the network structure changes
    para_g=list(np.array(tf.trainable_variables())[[0,1,4,5,8,9,12,13]])
    para_d=list(np.array(tf.trainable_variables())[[14,15,16,17,20,21,24,25,28,29]])

    # only update the weights for the discriminator network
    optimizer_op_d = tf.train.AdamOptimizer(learning_rate=alpha_d,beta1=beta1).minimize(d_loss,var_list=para_d)
    # only update the weights for the generator network
    optimizer_op_g = tf.train.AdamOptimizer(learning_rate=alpha_g,beta1=beta1).minimize(g_loss,var_list=para_g)

    saver = tf.train.Saver(max_to_keep=50) 

    with tf.Session() as sess:  
      
        sess.run(tf.initialize_all_variables())        
        z_sample = np.random.normal(0, 0.33, size=[batch_size,z_size]).astype(np.float32)
        
        for epoch in tqdm(range(training_epochs)):
            x = get_x(batch_size) 
            z = np.random.normal(0, 0.33, size=[batch_size,z_size]).astype(np.float32)
        
            # Update the discriminator and generator
            d_summary_merge = tf.merge_summary([summary_d_loss, summary_d_x_hist,summary_d_z_hist])

            summary_d, discriminator_loss = sess.run([d_summary_merge,d_loss],feed_dict={z_vector:z, x_vector:x})
            summary_g, generator_loss = sess.run([summary_g_loss,g_loss],feed_dict={z_vector:z})  
            
            if discriminator_loss <= 4.6*0.1: 
                sess.run([optimizer_op_g],feed_dict={z_vector:z})
            elif generator_loss <= 4.6*0.1:
                sess.run([optimizer_op_d],feed_dict={z_vector:z, x_vector:x})
            else:
                sess.run([optimizer_op_d],feed_dict={z_vector:z, x_vector:x})
                sess.run([optimizer_op_g],feed_dict={z_vector:z})
                            
            print "epoch: ",epoch,', d_loss:',discriminator_loss,'g_loss:',generator_loss

            # output generated chairs
            if epoch % 500 == 0:
                g_chairs = sess.run(net_g_test.outputs,feed_dict={z_vector:z_sample})
                if not os.path.exists(train_sample_directory):
                    os.makedirs(train_sample_directory)
                g_chairs.dump(train_sample_directory+'/'+str(epoch))
            
            if epoch % 500 == 0:
                if not os.path.exists(model_directory):
                    os.makedirs(model_directory)      
                saver.save(sess, save_path = model_directory + '/' + str(epoch) + '.cptk')

def testGAN():
    ## TODO
    pass

def visualize():
    ## TODO
    pass

def saveModel():
    ## TODO
    pass