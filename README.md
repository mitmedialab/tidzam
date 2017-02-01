Trying out Git

Download Dataset
================
``
wget http://downloads.duhart-clement.fr/dataset_tidzam.tar.gz
tar -zxvf dataset_tidzam.tar.gz  
``

Build the dataset
=================
The dataset is composed of three files, the dataset_data file contains in line the spectrograms of each wav samples. The dataset_label file stores in line the corresponding classe numbers and the dataset_dic file defines the associations between classe number and their corresponding name extracted from their filename.
``
python src/data.py --build=./wav/ --out=./dataset_150x186
``

Dataset vizualisation
---------------------
The set of samples in the dataset --read= for a given classe can be vizualised as follow:
``
python src/data.py --read=./dataset_150x186 --show=12
``

Training of the Neural Network Model
====================================
The trainer will load the dataset defined in --train=, train the neural network defined in src/model.py and store the checkpoints in --out=/
``
mkdir checkpoints
python src/train.py --train=./dataset_150x186 --out=./checkpoints/
``

Neural Network vizualisation
----------------------------
The neural network architecture, prediction embeddinds and learning parameters can be vizualised with tensorboard.
``
tensorboard --logdir=checkpoints
``

Play the Neural Network
=======================
The following command plays the trained neural network --nn on the stream --play according to classe dictionary --dic. The operation is operated on windows of 500ms.
``
python src/analyzerVGG.py --play=stream.wav --dic=./dataset_150x186 --nn=checkpoints
``
