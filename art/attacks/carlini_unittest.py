from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf
import numpy as np
import unittest
import keras
import keras.backend as k
from keras.models import Sequential
from keras.layers import Dense, Flatten, Conv2D, MaxPooling2D

from art.attacks.carlini import CarliniL2Method
from art.classifiers.tensorflow import TFClassifier
from art.classifiers.keras import KerasClassifier
from art.utils import load_mnist, random_targets


class TestCarliniL2(unittest.TestCase):
    """
    A unittest class for testing the Carlini2 attack.
    """
    def test_tfclassifier(self):
        """
        First test with the TFClassifier.
        :return:
        """
        # Build a TFClassifier
        # Define input and output placeholders
        self._input_ph = tf.placeholder(tf.float32, shape=[None, 28, 28, 1])
        self._output_ph = tf.placeholder(tf.int32, shape=[None, 10])

        # Define the tensorflow graph
        conv = tf.layers.conv2d(self._input_ph, 4, 5, activation=tf.nn.relu)
        conv = tf.layers.max_pooling2d(conv, 2, 2)
        fc = tf.contrib.layers.flatten(conv)

        # Logits layer
        self._logits = tf.layers.dense(fc, 10)

        # Train operator
        self._loss = tf.reduce_mean(tf.losses.softmax_cross_entropy(logits=self._logits, onehot_labels=self._output_ph))
        optimizer = tf.train.AdamOptimizer(learning_rate=0.01)
        self._train = optimizer.minimize(self._loss)

        # Tensorflow session and initialization
        self._sess = tf.Session()
        self._sess.run(tf.global_variables_initializer())

        # Get MNIST
        batch_size, nb_train, nb_test = 100, 500, 5
        (x_train, y_train), (x_test, y_test), _, _ = load_mnist()
        x_train, y_train = x_train[:nb_train], y_train[:nb_train]
        x_test, y_test = x_test[:nb_test], y_test[:nb_test]

        # Train the classifier
        tfc = TFClassifier((0, 1), self._input_ph, self._logits, self._output_ph,
                           self._train, self._loss, None, self._sess)
        tfc.fit(x_train, y_train, batch_size=batch_size, nb_epochs=2)

        # First attack
        cl2m = CarliniL2Method(classifier=tfc, targeted=True, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {'y': random_targets(y_test, tfc.nb_classes)}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        target = np.argmax(params['y'], axis=1)
        y_pred_adv = np.argmax(tfc.predict(x_test_adv), axis=1)
        self.assertTrue((target == y_pred_adv).all())

        # Second attack
        cl2m = CarliniL2Method(classifier=tfc, targeted=False, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {'y': random_targets(y_test, tfc.nb_classes)}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        target = np.argmax(params['y'], axis=1)
        y_pred_adv = np.argmax(tfc.predict(x_test_adv), axis=1)
        self.assertTrue((target != y_pred_adv).all())

        # Third attack
        cl2m = CarliniL2Method(classifier=tfc, targeted=False, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        y_pred = np.argmax(tfc.predict(x_test), axis=1)
        y_pred_adv = np.argmax(tfc.predict(x_test_adv), axis=1)
        self.assertTrue((y_pred != y_pred_adv).all())

    def test_krclassifier(self):
        """
        Second test with the KerasClassifier.
        :return:
        """
        # Initialize a tf session
        session = tf.Session()
        k.set_session(session)

        # Get MNIST
        batch_size, nb_train, nb_test = 100, 500, 5
        (x_train, y_train), (x_test, y_test), _, _ = load_mnist()
        x_train, y_train = x_train[:nb_train], y_train[:nb_train]
        x_test, y_test = x_test[:nb_test], y_test[:nb_test]

        # Create simple CNN
        model = Sequential()
        model.add(Conv2D(4, kernel_size=(5, 5), activation='relu', input_shape=(28, 28, 1)))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Flatten())
        model.add(Dense(10, activation='softmax'))

        model.compile(loss=keras.losses.categorical_crossentropy, optimizer=keras.optimizers.Adam(lr=0.01),
                      metrics=['accuracy'])

        # Get classifier
        krc = KerasClassifier((0, 1), model, use_logits=False)
        krc.fit(x_train, y_train, batch_size=batch_size, nb_epochs=2)

        # First attack
        cl2m = CarliniL2Method(classifier=krc, targeted=True, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {'y': random_targets(y_test, krc.nb_classes)}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        target = np.argmax(params['y'], axis=1)
        y_pred_adv = np.argmax(krc.predict(x_test_adv), axis=1)
        self.assertTrue((target == y_pred_adv).any())

        # Second attack
        cl2m = CarliniL2Method(classifier=krc, targeted=False, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {'y': random_targets(y_test, krc.nb_classes)}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        target = np.argmax(params['y'], axis=1)
        y_pred_adv = np.argmax(krc.predict(x_test_adv), axis=1)
        self.assertTrue((target != y_pred_adv).all())

        # Third attack
        cl2m = CarliniL2Method(classifier=krc, targeted=False, max_iter=10, binary_search_steps=10,
                               learning_rate=2e-2, initial_const=3, decay=1e-2)
        params = {}
        x_test_adv = cl2m.generate(x_test, **params)
        self.assertFalse((x_test == x_test_adv).all())
        y_pred = np.argmax(krc.predict(x_test), axis=1)
        y_pred_adv = np.argmax(krc.predict(x_test_adv), axis=1)
        self.assertTrue((y_pred != y_pred_adv).any())


if __name__ == '__main__':
    unittest.main()
