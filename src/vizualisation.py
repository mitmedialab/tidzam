import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
import data as tiddata
import numpy as np

# Build Metadata file for tensorflow Embedding Vizualisation
# For each row in Y, right its classes number in out_file file
def build_metadatafile(Y, out_file='database/metadata.tsv'):
    names = [a for a in range(0,Y.shape[1])]
    metadata_file = open(out_file, 'a')
    for i in range(Y.shape[0]):
        metadata_file.write('%d\n' % (np.argmax(Y[i])))
    metadata_file.close()

def feed_embeddings(embedding_var, dataset_t, Pout, Pin,
            nb_embeddings=1,
            sess=False,
            checkpoint_dir='checkpoints/'):
    if sess is False:
        sess = tf.get_default_session()
    # Clean previous embedding for this place
    with open(checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv', "w"):
        pass
    # Feed the network and stoire results
    dataset_t.split_dataset(p=1.0)
    bx, by = dataset_t.next_batch_train(batch_size=nb_embeddings)
    res = sess.run(Pout,feed_dict={Pin: bx} )
    embedding_var.assign(res)
    build_metadatafile(by, out_file=checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv')

    embeddings_writer = tf.train.SummaryWriter(checkpoint_dir)
    config_projector = projector.ProjectorConfig()
    embedding = config_projector.embeddings.add()
    embedding.tensor_name = embedding_var.name
    embedding.metadata_path = checkpoint_dir+'/metadata-'+embedding_var.name.replace('/','-')+'.tsv'
    projector.visualize_embeddings(embeddings_writer, config_projector)

def getFilter(W_a): # [5, 5, 1, 32]
    with tf.name_scope('Visualize_filters') as scope:
        print('* Visualize_filters generation')
        # In this section, we visualize the filters of the first convolutional layers
        # We concatenate the filters into one image
        # Credits for the inspiration go to Martin Gorner

        # input  [5, 5, 1, 32]
        Wpad= tf.zeros([5, 5, 1, 1])        # [5, 5, 1, 4]  - four zero kernels for padding
        # We have a 6 by 6 grid of kernepl visualizations. yet we only have 32 filters
        # Therefore, we concatenate 4 empty filters
        W_b = tf.concat(3, [W_a, Wpad, Wpad, Wpad, Wpad])   # [5, 5, 1, 36]
        W_c = tf.split(3, 36, W_b)         # 36 x [5, 5, 1, 1]
        W_row0 = tf.concat(0, W_c[0:6])    # [30, 5, 1, 1]
        W_row1 = tf.concat(0, W_c[6:12])   # [30, 5, 1, 1]
        W_row2 = tf.concat(0, W_c[12:18])  # [30, 5, 1, 1]
        W_row3 = tf.concat(0, W_c[18:24])  # [30, 5, 1, 1]
        W_row4 = tf.concat(0, W_c[24:30])  # [30, 5, 1, 1]
        W_row5 = tf.concat(0, W_c[30:36])  # [30, 5, 1, 1]
        W_d = tf.concat(1, [W_row0, W_row1, W_row2, W_row3, W_row4, W_row5]) # [30, 30, 1, 1]
        W_e = tf.reshape(W_d, [1, 30, 30, 1])
        Wtag = tf.placeholder(tf.string, None)
        # tf.summary.image("Visualize_kernels", W_e)
        return W_e
        #tf.image_summary("Visualize_kernels", W_e)

### Feature Map extraction
def plotNNFilter(units, out=None, show=None):
    filters = units.shape[3]
    f = plt.figure(1, figsize=(50,50))
    n_columns = 6
    n_rows = math.ceil(filters / n_columns) + 1
    for i in range(filters):
        plt.subplot(n_rows, n_columns, i+1)
        plt.imshow(units[0,:,:,i], interpolation="nearest", cmap="gray")

    if show is not None:
        plt.show()

    if out is not None:
        f.savefig(out)

def getActivations(layer,stimuli=None, out=None):
    if stimuli is not None:
        units = sess.run(layer,feed_dict={X:np.reshape(stimuli,[stimuli.shape[0],n_input],order='F'),keep_prob:1.0})
    else:
        units = sess.run(layer)
    plotNNFilter(units, out)
