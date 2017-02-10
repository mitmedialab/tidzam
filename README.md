Dependencies
============
python-scipy
python-matplotlib
pip install sounddevice --user
TensorFlow
TFlearn

Download Dataset
================
``
wget http://downloads.duhart-clement.fr/dataset_tidzam.tar.gz
tar -zxvf dataset_tidzam.tar.gz  
``

Build the dataset
=================
The dataset is composed of three files, the dataset_data file contains in line the spectrograms of each wav samples. The dataset_label file stores in line the corresponding classe numbers and the dataset_dic file defines the associations between classe number and their corresponding name extracted from their filename.

```
Usage: python src/data.py --stream=stream.wav

Options:
  -h, --help            show this help message and exit
  -w WAV, --wav=WAV     
  -d OPEN, --dataset=OPEN
                        Open an exisiting dataset
  -o OUT, --out=OUT     Provide output dataset name for wav processing.
  -s CLASSE_ID, --show=CLASSE_ID
                        Show spectrograms for a specific class_id
  --stream=STREAM       Sample extraction from an audio stream [WAV/OGG/MP3].
  --editor              Interractive mode.
```
Loading from WAV folder
-----------------------
``
python src/data.py --wav=./wav/ --out=./dataset_150x186
``

Editor from audio stream
----------------------------
Create a new dataset to build from --input=stream:
``
python src/data.py --input=stream.wav --editor
``
Build from an exisiting dataset --dataset= from --input= audio stream.
``
python src/data.py --input=stream.wav --out=dataset_150x186.out --dataset=dataset_150x186 --editor
``

Dataset vizualisation
---------------------
The set of samples in the dataset --read= for a given classe can be vizualised as follow:
``
python src/data.py --dataset=./dataset_150x186 --show=12
``
Print all samples in the dataset:
``
python src/data.py --input=./dataset_150x186
``

Training of the Neural Network Model
====================================
The trainer will load the dataset defined in --train=, train the neural network defined in src/model.py and store the checkpoints in --out=/

Disable GPU ?
-------------
Need 6GB RAM memory on GPU
``
export CUDA_VISIBLE_DEVICES=''
``
```
Usage: train.py --dataset=dataset_150x186 --out=build/ -dnn=test [OPTIONS]

Options:
  -h, --help            show this help message and exit
  -d DATASET, --dataset=DATASET
                        Define the dataset to train.
  -o OUT, --out=OUT     Define output folder to store the neural network and
                        checkpoints.
  --training-iterations=TRAINING_ITERS
                        Number of training iterations (Default: 400
                        batchsize).
  --batchsize=BATCH_SIZE
                        Size of the training batch (Default:64).
  --embeddings=NB_EMBEDDINGS
                        Number of embeddings to compute (default: 50)..
  --learning-rate=LEARNING_RATE
                        Learning rate (default: 0.001).
  --dnn=DNN             DNN model to train (Default: ).
  --embeddings-step=EMBEDDINGS_STEP
                        Step period to compute embeddings and feature maps
                        (Default: 1).
```

Neural Network vizualisation
----------------------------
The neural network architecture, prediction embeddinds and learning parameters can be vizualised with tensorboard.
``
tensorboard --logdir=checkpoints
``

Play the Neural Network
=======================
The following command return the output predictions of the neural network on all channels of the audio stream withe time windows of 500ms.

```
Usage: analyzer.py --nn=build/test --stream=stream.wav [--show, -h]

Options:
  -h, --help            show this help message and exit
  -s STREAM, --stream=STREAM
                        Input audio stream to analyze.
  -n NN, --nn=NN        Neural Network session to load.
  --show                Play the audio samples and show their spectrogram.
```
