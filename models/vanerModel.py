import numpy as np
import util
import tensorflow as tf
import os
from tensorflow.python import pywrap_tensorflow

class vanerModel(object):
    def __init__(self, sess, **kwargs):
        print (kwargs)
        self.V = tf.get_variable('V', shape=[kwargs['n'], kwargs['q']],
                                  trainable=True)
        self.T = tf.get_variable('T', shape=[kwargs['q'], kwargs['p']], 
                                  trainable=True)
        self.W_ = tf.placeholder(tf.float32, shape=[kwargs['n'], kwargs['p']])
        self.A_ = tf.placeholder(tf.float32, shape=[kwargs['n'], kwargs['n']])

        self.loss = tf.add(
                tf.square(tf.norm(tf.subtract(tf.matmul(self.V, self.T), self.W_),
                        ord='fro', axis=(-2,-1))),
                tf.multiply(kwargs['lambda'], tf.square(tf.norm(tf.subtract(self.A_, 
                    tf.matmul(self.V, tf.transpose(self.V)) ), ord='fro', axis=(-2,-1))))
            )
        # self.loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=self.label_, logits=self.logits))
        
        self.learning_rate = tf.Variable(float(kwargs['learning_rate']), trainable=False, dtype=tf.float32)
        self.learning_rate_decay = self.learning_rate.assign(self.learning_rate * kwargs['learning_rate_decay'])

        self.global_step = tf.Variable(0, trainable=False)
        self.params = tf.trainable_variables()
        print(self.params)

        self.train_op = tf.train.AdamOptimizer(self.learning_rate).minimize(self.loss, global_step=self.global_step, var_list=self.params)
        sess.run(tf.global_variables_initializer())


    def save_model(self, sess, **kwargs):
        saver = tf.train.Saver()
        if not os.path.exists("data/save_model"):
            os.mkdir("data/save_model")
        modelPath = "data/save_model/"
        checkpoint_path = modelPath + "vanerModel.ckpt"
        saver.save(sess, checkpoint_path)
        reader=pywrap_tensorflow.NewCheckpointReader(checkpoint_path)
        var_to_shape_map=reader.get_variable_to_shape_map()

        for key in var_to_shape_map:
            str_name = key
            if str_name.find('Adam') > -1:
                continue
            # print('tensor_name:' , str_name)
            if (str_name == 'V'):
                V = reader.get_tensor(key)
            if (str_name == 'T'):
                T = reader.get_tensor(key)
        np.save("data/vanerModel_V.npy", V)
        np.save("data/vanerModel_T.npy", T)


    def train_epoch(self, sess, A, W, best_loss, **kwargs):
        epoch_size = 10
        for _ in range(epoch_size):
            loss_, __ = sess.run([self.loss, self.train_op], feed_dict={self.A_: A, self.W_: W})
            print("loss = %.3f" % (loss_))
            if (loss_ < best_loss):
                best_loss = loss_
                self.save_model(sess, **kwargs)
        return best_loss
        # print( tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope='encoder'))


def cosine_distance(x, y):
    return 1. * np.dot(x, y) / np.linalg.norm(x) / np.linalg.norm(y)


def train(sess, A, W, **kwargs):
    print ("Begin Training")
    model = vanerModel(sess, **kwargs)
    train_times = 5
    best_loss = 10000000.
    for _ in range(train_times):
        best_loss = model.train_epoch(sess, A, W, best_loss, **kwargs)
        print("epoch : %d" % ( _ )) 


def trainVanerModel(sess, trainData, trainLabel, trainIndex, a, W, **kwargs):
    base_n = len(trainIndex)
    feature_n = trainData.shape[1]

    # Calculate Vector x (avg_x):
    x = np.zeros(shape=[base_n, feature_n], dtype=np.float32)
    print ("base_n = %d feature_n = %d" % (base_n, feature_n))
    for i in range(base_n):
        sum = 0.
        t = trainData[trainIndex[i]]
        x[i] = np.mean(t, axis=0)
    print("Vector x complete.")

    # Calculate Matrix A:
    # -- TODO: Rewrite this --

    # A = np.zeros(shape=[base_n, base_n], dtype=np.float32)
    # for i in range(base_n):
    #     for j in range(base_n):
    #         A[i][j] = cosine_distance(x[i], x[j])
    # np.save('data/A.npy', A)
    A = np.load('data/A.npy')
    
    model = train(sess, A, W, **kwargs)  
    print("Training complete.")
    #if (a != None):

    m = a.shape[0]
    a_new = np.zeros(shape=[m, base_n], dtype=np.float32)
    for i in range(m):
        for j in range(base_n):
            a_new[i][j] = cosine_distance(a[i], x[j])

    V = tf.constant(np.load("data/vanerModel_V.npy"))
    T = tf.constant(np.load("data/vanerModel_T.npy"))
    
    v_new = tf.matmul(a_new, tf.matmul(tf.matrix_inverse(tf.matmul(V, tf.transpose(V))), V))
    w_new = tf.matmul(v_new, T)

    with sess.as_default():
        np.save('data/W_new.npy', w_new.eval())

    return w_new

