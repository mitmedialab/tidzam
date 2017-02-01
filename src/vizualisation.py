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

def create_embeddings(res, embedding_name,
            sess=False,
            checkpoint_dir='.',
            metadatafile_dir='database/'):
    if sess is False:
        sess = tf.get_default_session()
    # Create the embeddings
    res = tf.Variable(res, name=embedding_name, trainable=False)
    sess.run(res.initializer)
    embeddings_writer = tf.summary.FileWriter(checkpoint_dir + "/",sess.graph)
    config_projector = projector.ProjectorConfig()
    embedding = config_projector.embeddings.add()
    embedding.tensor_name = embedding_name
    embedding.metadata_path = metadatafile_dir+'/metadata-'+embedding_name+'.tsv'
    projector.visualize_embeddings(embeddings_writer, config_projector)

def feed_embeddings(dataset_t, Pout, Pin,
            sess=False,
            checkpoint_dir='checkpoints/',
            embedding_name='predictions'):
    if sess is False:
        sess = tf.get_default_session()
    # Clean previous embedding for this place
    with open(checkpoint_dir+'/metadata-'+embedding_name+'.tsv', "w"):
        pass
    # Feed the network and stoire results
    dataset_t.split_dataset(p=1.0)
    for i in range(0, dataset_t.batch_train_count()/10):
        bx, by = dataset_t.next_batch_train()
        a = sess.run(Pout,feed_dict={Pin: bx} )
        try:
            res = np.concatenate((res,a), axis=0)
        except NameError:
            res = a
        build_metadatafile(by, out_file=checkpoint_dir+'/metadata-'+embedding_name+'.tsv')
    create_embeddings(res, embedding_name,
                        checkpoint_dir=checkpoint_dir,
                        metadatafile_dir=checkpoint_dir)
    print("Embedding create for " + embedding_name)

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
