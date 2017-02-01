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
Help:
-----
```
Usage: train.py --train=dataset --out=folder_dest [options]

Options:
  -h, --help            show this help message and exit
  -t TRAIN, --train=TRAIN
                        Define the dataset to train.
  -o OUT, --out=OUT     Define output folder to store the neural network and
                        checkpoints.
  --embeddings=NB_EMBEDDINGS
                        Number of embeddings to generate (default: 0).
  --display-step=DISPLAY_STEP
                        Period to compute cost and accuracy functions
                        (Default: 5).
  --saving-step=SAVING_PERIOD
                        Period to save the session (Default: 5).
  --learning-rate=LEARNING_RATE
                        Set the learning rate (Default: 0.001).
  --dropout=DROPOUT     Set the dropout probability rate (Default: 0.75).
  --batchsize=BATCH_SIZE
                        Set the learning rate (Default: 0.001).
```

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
