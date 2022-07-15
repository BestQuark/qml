r"""
.. _learning_few_data:

Generalization in QML from few training data
============================================

.. meta::
    :property="og:description": Generalization of quantum machine learning models.
    :property="og:image": https://pennylane.ai/qml/_images/few_data_thumbnail.png

.. related::

    tutorial_local_cost_functions Alleviating barren plateaus with local cost functions

*Authors: Korbinian Kottmann, Luis Mantilla Calderon, Maurice Weber. Posted: 01 June 2022*

In this tutorial we dive into the generalization capabilities of quantum machine learning models.
For the example of a Quantum Convolutional Neural Nework (QCNN), we show how its generalization error behaves as a
function of the number of training samples. This demo is based on the paper
*"Generalization in quantum machine learning from few training data"*. by Caro et al. [#CaroGeneralization]_.

What is Generalization in (Q)ML?
------------------------
When optimizing a machine learning model, be it classical or quantum, we aim to maximize its performance over the data
distribution of interest, like for example images of cats and dogs. However, in practice we are limited to a finite amount of
data, which is why it is necessary to reason about how our model performs on new, previously unseen data. The difference
between the model's performance on the true data distribution, and the performance estimated from our training data is
called the *generalization error* and indicates how well the model has learned to generalize to unseen data.

.. figure:: /demonstrations/learning_few_data/true_vs_sample.png
    :width: 75%
    :align: center

It is good to know that generalization can be seen as a manifestation of the bias-variance trade-off: models which
perfectly fit the training data, i.e. which admit a low bias, have a higher variance, typically perform poorly on unseen
test data and don't generalize well. In the classical machine learning community, this trade off has been extensively
studied and has lead to optimization techniques which favour generalization, for example by regularizing models via
their variance [#NamkoongVariance]_.

Let us now dive deeper into generalization properties of quantum machine learning (QML) models. We start by describing
the typical data processing pipeline of a QML model. A classical data input :math:`x` is first encoded in a quantum
state via a mapping :math:`x \mapsto \rho(x)`. This encoded state is then processed through a parametrized quantum
channel :math:`\rho(x) \mapsto \mathcal{E}_\alpha(\rho(x))` and a measurement is performed on the resulting state
to get the final prediction. The goal is now to minimize the expected loss over the data generating distribution
:math:`P` indicating how well our model performs on new data. Mathematically, for a loss function :math:`\ell`, the
expected loss is given by

.. math:: R(\alpha) = \mathbb{E}_{(x,y)\sim P}[\ell(\alpha;\,x,\,y)].

As :math:`P` is generally unknown, in practice this quantity has to be estimated from a finite amount of data. Given
a training set :math:`S = \{(x_i,\,y_i)\}_{i=1}^N`, we estimate the performance of our QML model by calculating the
average loss over the training set

.. math:: \hat{R}_S(\alpha) = \frac{1}{N}\sum_{i=1}^N \ell(\alpha;\,x_i,\,y_i)

which is referred to as the training loss and is an unbiased estimate of :math:`R(\alpha)`. This is only a proxy
to the true quantity of interest :math:`R(\alpha)` and their difference is called the generalization error

.. math:: \mathrm{gen}(\alpha) = \hat{R}_S(\alpha) - R(\alpha)

which is the quantity that we explore in this tutorial. Keeping in mind the bias-variance trade off, one would expect
that more complex models, i.e. models with a larger number of parameters, achieve a lower error on the training data,
but a higher generalization error. Having more training data on the other hand leads to a better approximation of the
true expected loss and hence lower generalization error. This intuition is made precise in Ref. [#CaroGeneralization]_
where it is shown that :math:`\mathrm{gen}(\alpha)` roughly scales as :math:`\mathcal{O}(\sqrt{T / N})` where :math:`T`
is the number of parametrized gates and :math:`N` is the number of training samples.
"""

##############################################################################
# Generalization Bounds for Quantum Machine Learning Models
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# As hinted at earlier, we expect the generalization error to depend both on the richness of the model class, as well as
# on the amount of training data available. As a first result, the authors of Ref. [#CaroGeneralization]_ found that for
# a QML model with at most :math:`T` parametrized local quantum channels, the generalization error depends on :math:`T`
# and :math:`N` according to
#
# .. math:: \mathrm{gen}(\alpha) \in \mathcal{O}\left(\sqrt{\frac{T\log T}{N}}\right).
#
# We see that this scaling is in line with our intuition that the generalization error scales inversely with the number
# of training samples, and increases with the number of parametrized gates. However, as is the case for quantum
# convolutional neural networks, it is possible to get a more fine-grained bound by including knowledge on the number of
# gates :math:`M` which have been reused. Naively, one could suspect that the generalization error scales as
# :math:`\tilde{\mathcal{O}}(\sqrt{MT/N})` by directly applying the above result (and where
# :math:`\tilde{\mathcal{O}}` includes logarithmic factors). However, the authors of Ref. [#CaroGeneralization]_ found
# that such models actually adhere to the better scaling
#
# .. math:: \mathrm{gen}(\alpha) \in \mathcal{O}\left(\sqrt{\frac{T\log MT}{N}}\right).
#
# With this we see that for QCNNs to have a generalization error :math:`\mathrm{gen}(\alpha)\leq\epsilon`, we need a
# training set of size :math:`N \sim T \log MT / \epsilon^2`. For the special case of QCNNs, we can explicitly connect
# the number of samples needed for good generalization to the system size :math:`n` since these models
# use :math:`\mathcal{O}(\log(n))` independendently parametrized gates, each of which is used at most :math:`n` times.
# Putting the pieces together, we find that a training set of size
#
# .. math::  N \in \mathcal{O}(\mathrm{poly}(\log n))
#
# is sufficient for the generalization error to be bounded by :math:`\mathrm{gen}(\alpha) \leq \epsilon`.
# In the next part of this tutorial, we will illustrate this result by implementing a QCNN to classify different
# digits in the classical ``digits`` dataset. Before that, we set up our QCNN.

##############################################################################
# Quantum convolutional neural network
# ------------------------------------
# Before we start building a quantum CNN, let us remember the idea of their classical counterpart.
# Classical CNNs are a family of neural network with a specific type of architecture aimed to 
# perform image processing. To achieve this goal, one uses what is known as a *convolutional layer*, 
# which consists of a small kernel (a window) that sweeps a 2D array (an image) and extracts local 
# information about such an array. In addition, depending on the purpose of your CNN, one might want
# to do classification or feature preduction, which are arrays much smaller than the original image.
# To deal with this dimensionality difference, one uses what is known as a *pooling layer*. These 
# layers are used to reduce the dimensionality of the 2D array being processed (whereas inverse pooling increase the
# dimensionality of a 2D array). Finally, one takes these two layers and apply them repeatedly and
# interchangeably. We want to build something similar for a quantum circuit. 
# 
# First, let us import a few libraries that we will use along this demo. 

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn import datasets
import seaborn as sns
from tqdm.auto import trange

import jax
import jax.numpy as jnp

import pennylane as qml
import pennylane.numpy as pnp

sns.set()

seed = 0
rng = np.random.default_rng(seed=seed)

##############################################################################
# To construct a convolutional and pooling layer in a quantum circuit, we will
# follow the QCNN construction proposed by [#CongQuantumCNN]_. The former layer 
# will extract local correlations, while the latter allows reducing the dimensionality
# of the feature vector. In a qubit circuit, the convolutional layer, which consists of a kernel that
# is sweept along all the image, is now translated to a two-qubit unitary that correlates neighbouring
# qubits. As for the pooling layer, we will use a conditioned single qubit unitary that depends on
# the measurement of a neighbouring qubit. Finally, we use a "dense layer" that entangles all qubits
# of the final state using a all-to-all unitary gate. 
# 
# **Let's break down each layer:**
#
# The convolutional layer should has as an input the weights of the two-qubit unitary which are to 
# be determined in the training rounds. In ``pennylane``, we model this arbitrary two-qubit unitary
# with two single-qubit gates ``qml.U3`` (parametrized by three parameters, each), followed by an three ising 
# interaction between both qubits (each interaction is parametrized by one parameter), and two additional
# ``qml.U3``` gates in each qubit. 

def convolutional_layer(weights, wires, skip_first_layer=True):
    n_wires = len(wires)
    assert n_wires >= 3, "this circuit is too small!"

    for p in [0, 1]:
        for indx, w in enumerate(wires):
            if indx % 2 == p and indx < n_wires - 1:
                if indx % 2 == 0 and skip_first_layer:
                    qml.U3(*weights[:3], wires=[w])
                    qml.U3(*weights[3:6], wires=[wires[indx + 1]])
                qml.IsingXX(weights[6], wires=[w, wires[indx + 1]])
                qml.IsingYY(weights[7], wires=[w, wires[indx + 1]])
                qml.IsingZZ(weights[8], wires=[w, wires[indx + 1]])
                qml.U3(*weights[9:12], wires=[w])
                qml.U3(*weights[12:], wires=[wires[indx + 1]])

##############################################################################
# The pooling layer has as inputs the weights of the single-qubit conditional unitaries, which in 
# this case, are ``qml.U3`` gates. Then, we apply these conditional measurement to half of the 
# unmeasured wires, reducing our system size by half. 

def pooling_layer(weights, wires):
    n_wires = len(wires)
    assert len(wires) >= 2, "this circuit is too small!"

    for indx, w in enumerate(wires):
        if indx % 2 == 1 and indx < n_wires:
            m_outcome = qml.measure(w)
            qml.cond(m_outcome, qml.U3)(*weights, wires=wires[indx - 1])


##############################################################################
# Combining both layers together, and using a arbitrary unitary to model a dense layer,
# we can construct a quantum CNN, which will take as input a set of features (the image),
# encode this features using an embedding map, apply rounds of convolutional and pooling layers,
# and eventually get the desired measurement statistics of the circuit. 

def conv_and_pooling(kernel_weights, n_wires):
    convolutional_layer(kernel_weights[:15], n_wires)
    pooling_layer(kernel_weights[15:], n_wires)


def dense_layer(weights, wires):
    qml.ArbitraryUnitary(weights, wires)

num_wires = 6
device = qml.device('default.qubit', wires=num_wires)

@qml.qnode(device, interface="jax")
def conv_net(weights, last_layer_weights, features):
    # assert weights.shape[0] == 18, "The size of your weights vector is incorrect!"

    layers = weights.shape[1]
    wires = list(range(num_wires))

    # inputs the state input_state
    qml.AmplitudeEmbedding(features=features, wires=wires, pad_with=0.5)

    # adds convolutional and pooling layers
    for j in range(layers):
        conv_and_pooling(weights[:, j], wires)
        wires = wires[::2]

    assert (
            last_layer_weights.size == 4 ** (len(wires)) - 1
    ), f"The size of the last layer weights vector is incorrect! \n Expected {4 ** (len(wires)) - 1}, Given {last_layer_weights.size}"
    dense_layer(last_layer_weights, wires)
    return qml.probs(wires=(0))


##############################################################################
# In the problem we will address, we will need to encode 64 features
# in the state to be processed by the QCNN. Thus, we require 6 qubits to encode
# each feature value in the amplitude of each computational basis state. 
#
# Training the QCNN on the digits dataset
# ---------------------------------------
# In this demo, we are going to classify the digits ``0`` and ``1`` from the classical ``digits`` dataset.
# The following function helps load the dataset from ``sklearn.dataset``. Further, we provide utility functions
# for evaluating the cost and accuracy of our classification.

def load_digits_data(num_train, num_test, rng):
    digits = datasets.load_digits()
    features, labels = digits.data, digits.target

    # only use first two classes
    features = features[np.where((labels == 0) | (labels == 1))]
    labels = labels[np.where((labels == 0) | (labels == 1))]

    # normalize data
    features = features / np.linalg.norm(features, axis=1).reshape((-1, 1))

    # subsample train and test split
    train_indices = rng.choice(len(labels), num_train, replace=False)
    test_indices = rng.choice(np.setdiff1d(range(len(labels)), train_indices), num_test, replace=False)

    x_train, y_train = features[train_indices], labels[train_indices]
    x_test, y_test = features[test_indices], labels[test_indices]

    return jnp.asarray(x_train), jnp.asarray(y_train), jnp.asarray(x_test), jnp.asarray(y_test)

##############################################################################
# Computing the accuracy and cost of our training objective.

def compute_out(weights, weights_last, features, labels):
    """Computes the output of the corresponding label in the qcnn"""
    cost = lambda weights, weights_last, feature, label: conv_net(weights, weights_last, feature)[label]
    return jax.vmap(cost, in_axes=(None, None, 0, 0), out_axes=0)(weights, weights_last, features, labels)

@jax.jit
def compute_accuracy(weights, weights_last, features, labels):
    """Computes the accuracy over the provided features and labels"""
    out = compute_out(weights, weights_last, features, labels)
    return jnp.sum(out > 0.5)/len(out)

@jax.jit
def compute_cost(weights, weights_last, features, labels):
    """Computes the cost over the provided features and labels"""
    out = compute_out(weights, weights_last, features, labels)
    return 1.0 - jnp.sum(out) / len(labels)

##############################################################################
# Weights initialization.
def init_weights():
    weights = pnp.random.normal(loc=0, scale=1, size=(18, 2), requires_grad=True)
    weights_last = pnp.random.normal(loc=0, scale=1, size=4 ** 2 - 1, requires_grad=True)
    return jnp.array(weights), jnp.array(weights_last)



##############################################################################
# We are going to perform the classification for differently sized training sets. We therefore define the classification procedure once and then perform it for different
# datasets.

def train_qcnn(n_train, n_test, n_epochs, desc):
    """
    Args:
        n_train  (int): number of training examples
        n_test   (int): number of test examples
        n_epochs (int): number of training epochs
        desc  (string): displayed string during optimization

    Returns:
        dict: n_train, steps, train_cost_epochs, train_acc_epochs, test_cost_epochs, test_acc_epochs

    """
    # load data
    x_train, y_train, x_test, y_test = load_digits_data(n_train, n_test, rng)

    # init weights and optimizer
    weights, weights_last = init_weights()
    optimizer = qml.AdamOptimizer(stepsize=0.01)

    # data containers
    train_cost_epochs, test_cost_epochs, train_acc_epochs, test_acc_epochs = [], [], [], []

    pbar = trange(n_epochs, desc=desc)

    for step in pbar:
        (weights, weights_last), train_cost = optimizer.step_and_cost(
            compute_cost, weights, weights_last, features=x_train, labels=y_train
        )
        train_cost_epochs.append(train_cost)

        # compute accuracy on training data
        train_acc = compute_accuracy(weights, weights_last, x_train, y_train)
        train_acc_epochs.append(train_acc)

        # compute cost on testing data
        test_cost = compute_cost(weights, weights_last, x_test, y_test)
        test_cost_epochs.append(test_cost)

        # compute accuracy on testing data
        test_acc = compute_accuracy(weights, weights_last, x_test, y_test)
        test_acc_epochs.append(test_acc)

        pbar.set_postfix(train_cost=train_cost, test_cost=test_cost, train_acc=train_acc, test_acc=test_acc)

    return dict(
        n_train=[n_train] * n_epochs,
        step=np.arange(1, n_epochs+1, dtype=int),
        train_cost=train_cost_epochs,
        train_acc=train_acc_epochs,
        test_cost=test_cost_epochs,
        test_acc=test_acc_epochs
    )

##############################################################################
# Training for different training set sizes yields different accuracies, as can be seen below. As we increase the training data size, the the overall test accuracy,
# a proxy for the models' generalization capabilities, increases.

n_test = 100
n_epochs = 20

# train on 40 train samples
results = train_qcnn(n_train=40, n_test=100, n_epochs=n_epochs, desc=f'n=20')

# write results to dataframe
results_df = pd.DataFrame(columns=['train_acc', 'train_cost', 'test_acc', 'test_cost', 'step', 'n_train'])
results_df = pd.concat([results_df, pd.DataFrame.from_dict(results)], axis=0, ignore_index=True)

##############################################################################
# make some pretty plots...

def make_plot(df, n_train):
    fig, axs = plt.subplots(ncols=3, figsize=(14,5))

    ax = axs[0]
    ax.plot(df.train_cost, "x--", label="train")
    ax.plot(df.test_cost, "x--", label="test")
    ax.set_ylabel("loss", fontsize=18)
    ax.set_xlabel("epoch", fontsize=18)
    ax.legend(fontsize=14)

    ax = axs[1]
    ax.plot(df.train_acc,"o:", label=f"train")
    ax.plot(df.test_acc,"x--", label=f"test")
    ax.set_ylabel("accuracy", fontsize=18)
    ax.set_xlabel("epoch", fontsize=18)
    ax.legend(fontsize=14)

    ax = axs[2]
    ax.plot(df.train_acc, results_df.test_acc,"o:", label='N=40')
    ax.set_xlim(df.test_acc.min()-0.05, 1.05)
    ax.plot(np.linspace(df.test_acc.min(), 1.0), np.linspace(df.test_acc.min(), 1.0), ls='--', color='black')
    ax.set_ylabel("test accuracy", fontsize=18)
    ax.set_xlabel("train accuracy", fontsize=18)
    ax.legend(fontsize=14)

    fig.suptitle(f'Performance Measures for Training Set of Size $N=${n_train}', fontsize=20)
    plt.tight_layout()
    plt.show()

make_plot(results_df, n_train=40)


##############################################################################
# References
# ----------
#
# .. [#CaroGeneralization]
#
#     Matthias C. Caro, Hsin-Yuan Huang, M. Cerezo, Kunal Sharma, Andrew Sornborger, Lukasz Cincio, Patrick J. Coles.
#     "Generalization in quantum machine learning from few training data"
#     `arxiv:2111.05292 <https://arxiv.org/abs/2111.05292>`__, 2021.
#
# .. [#NamkoongVariance]
#
#     Hongseok Namkoong and John C. Duchi.
#     "Variance-based regularization with convex objectives."
#     `Advances in Neural Information Processing Systems
#     <https://proceedings.neurips.cc/paper/2017/file/5a142a55461d5fef016acfb927fee0bd-Paper.pdf>`__, 2017.
#
# .. [#CongQuantumCNN]
#
#     Iris Cong, Soonwon Choi, Mikhail D. Lukin.
#     "Quantum Convolutional Neural Networks"
#     `arxiv:1810.03787 <https://arxiv.org/abs/1810.03787>`__, 2018.
#
