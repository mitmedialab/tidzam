from __future__ import print_function

import sys, optparse
import numpy as np
import shutil
import time
import math
import os

import vizualisation as vizu
import TidzamDatabase as database
from App import App

if __name__ == "__main__":

    from tensorflow.contrib.tensorboard.plugins import projector
    import tensorflow as tf


    App.log(0, "TensorFlow "+ tf.__version__)

    ###################################
    ### Console Parameters
    ###################################
    usage="TidzamTrain.py --dataset-train=mydataset --dnn=models/model.py --out=save/ [OPTIONS]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--dataset-train",
        action="store", type="string", dest="dataset_train",
        help='Define the dataset to train.')

    parser.add_option("-t", "--dataset-test",
        action="store", type="string", dest="dataset_test",
        help='Define the dataset for evaluation.')

    parser.add_option("-o", "--out",
        action="store", type="string", dest="out",
        default="/tmp/tflearn_logs",
        help='Define output folder to store the neural network and trains.')

    parser.add_option("--dnn",
        action="store", type="string", dest="dnn", default="default",
        help='DNN model to train (Default: ).')
    ###
    parser.add_option("--training-iterations",
        action="store", type="int", dest="training_iters",default=20000,
        help='Number of training iterations (Default: 20000 iterations).')

    parser.add_option("--testing-step",
        action="store", type="int", dest="testing_iterations",default=10,
        help='Number of training iterations between each testing step (Default: 10).')

    parser.add_option("--batchsize",
        action="store", type="int", dest="batch_size",default=64,
        help='Size of the training batch (Default:64).')

    parser.add_option("--learning-rate",
        action="store", type="float", dest="learning_rate", default=0.001,
        help='Learning rate (default: 0.001).')
    ###
    parser.add_option("--stats-step",
        action="store", type="int", dest="STATS_STEP", default="20",
        help='Step period to compute statistics, embeddings and feature maps (Default: 10).')

    parser.add_option("--nb-embeddings",
        action="store", type="int", dest="nb_embeddings", default=50,
        help='Number of embeddings to compute (default: 50)..')
    ###
    parser.add_option("--job-type",
        action="store", type="string", dest="job_type", default="worker",
        help='Selector the process job: ps or worker (default:worker).')

    parser.add_option("--task-index",
        action="store", type="int", dest="task_index", default=0,
        help='Provide the task index to execute (default:0).')

    parser.add_option("--workers",
        action="store", type="string", dest="workers", default="localhost:2222",
        help='List of workers (worker1.mynet:2222,worker2.mynet:2222, etc).')

    parser.add_option("--ps",
        action="store", type="string", dest="ps", default="",
        help='List of parameter servers (ps1.mynet:2222,ps2.mynet:2222, etc).')

    parser.add_option("--class_file", action="store", type="string", dest="class_file" ,
        default="" , help="json file holding the data necessary about class access path and type")
    ###
    (opts, args) = parser.parse_args()


    ###################################
    # Cluster configuration
    ###################################
    ps      = opts.ps.split(",")
    workers = opts.workers.split(",")
    cluster  = {"worker":workers}
    if ps[0] != "":
        cluster["ps"] = ps
    cluster = tf.train.ClusterSpec(cluster)

    # start a server for a specific task
    server = tf.train.Server(cluster,   job_name=opts.job_type,
                                        task_index=opts.task_index)

    if opts.job_type == "ps":
        App.log(0, "Parameter server " + ps[opts.task_index]+ " started.")
        server.join()
    elif opts.job_type != "worker":
        App.log(0, "Bad argument in job name [ps | worker]")
        sys.exit(0)

    App.log(0, "Worker " + workers[opts.task_index]+ " started")

    gpu_options = tf.GPUOptions(
        per_process_gpu_memory_fraction=0.25,
        allow_growth=True
        )
    config = tf.ConfigProto(
            intra_op_parallelism_threads=4,
            inter_op_parallelism_threads=4,
            gpu_options=gpu_options,
#            log_device_placement=True,
            allow_soft_placement=True
            )


    ###################################
    # Load the data
    ###################################
    try:
        labels_dic = np.load(opts.out + "/labels_dic.npy")
    except:
        App.log(0 , "Couldn't find a label dic , a new one will be build")
        labels_dic = []

    dataset      = database.Dataset(opts.dataset_train , class_file=opts.class_file, labels_dic=labels_dic)
    if opts.dataset_test:
        dataset_test = database.Dataset(opts.dataset_test, class_file=opts.class_file, labels_dic=labels_dic)
    App.log(0, "Sample size: " + str(dataset.dataw) + 'x' + str(dataset.datah))

    ###################################
    # Between-graph replication
    ###################################
    with tf.device(tf.train.replica_device_setter(
        worker_device="/job:worker/task:%d" % opts.task_index,
        cluster=cluster)):

        global_step  = tf.train.get_or_create_global_step()
        writer_train = tf.summary.FileWriter(opts.out+"/model/train/")
        writer_test  = tf.summary.FileWriter(opts.out+"/model/test/")

        ###################################
        # Build graphs
        ###################################
        App.log(0, "Loading DNN model from:  " + opts.dnn)
        sys.path.append('./')
        exec("import "+os.path.dirname(opts.dnn)+"."+os.path.basename(opts.dnn).replace(".py","")+" as model")
        net = eval("model.DNN([dataset.dataw, dataset.datah], dataset.get_nb_classes())")

        ## Generate summaries
        with tf.name_scope('Summaries'):
            summaries = vizu.Summaries(net, dataset.get_nb_classes())

            ## Construct filter images
            with tf.name_scope('Visualize_filters'):
                summaries.build_kernel_filters_summaries(net.show_kernel_map)

        with tf.variable_scope("embeddings"):
            opts.nb_embeddings = min(opts.nb_embeddings, dataset.data.shape[0])
            proj      = projector.ProjectorConfig()
            embed_train     = vizu.Embedding("OUT_train", net.input, net.out, net.keep_prob, proj, opts.nb_embeddings, opts.out)
            embed_test      = vizu.Embedding("OUT_test",  net.input, net.out, net.keep_prob, proj, opts.nb_embeddings, opts.out)
            projector.visualize_embeddings(writer_test, proj)
            projector.visualize_embeddings(writer_train, proj)

        App.log(0, "Generate summaries graph.")
        merged = tf.summary.merge_all()

        with tf.name_scope('Trainer'):
            train_op = tf.train.AdagradOptimizer(opts.learning_rate).minimize(net.cost, global_step=global_step)
            hooks=[tf.train.StopAtStepHook(last_step=opts.training_iters)]

        ###################################
        # Start the session
        ###################################
        if opts.task_index != 0:
            App.log(0, "Waiting for the master worker.")
        with tf.train.MonitoredTrainingSession(master=server.target,
                                               is_chief=(opts.task_index == 0),
                                               checkpoint_dir=opts.out+"/model/",
                                               hooks=hooks,
                                               config=config) as sess:
                App.ok(0, "Training is starting.")
                writer_train.add_graph(sess.graph)
                writer_test.add_graph(sess.graph)

                shutil.copyfile(opts.dnn, opts.out + "/model.py")
                np.save(opts.out + "/labels_dic.npy", dataset.labels_dic)

                while not sess.should_stop():
                    App.log(0, "---")
                    start_time = time.time()

                    ################### TRAINING
                    batch_x, batch_y    = dataset.next_batch(batch_size=opts.batch_size)

                    _, step = sess.run( [train_op, global_step],
                        feed_dict={ net.input: batch_x, net.labels: batch_y, net.keep_prob: 0.5})

                    if step % opts.STATS_STEP == 0:
                        run_options         = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
                        run_metadata        = tf.RunMetadata()

                        _, accuracy_train, cost_train, summary_train = sess.run(
                            [train_op, summaries.accuracy, net.cost, merged],
                            feed_dict={ net.input: batch_x, net.labels: batch_y, net.keep_prob: 0.5},
                            options=run_options, run_metadata=run_metadata)

                        embed_train.evaluate(
                                    batch_x[:opts.nb_embeddings,:],
                                    batch_y[:opts.nb_embeddings,:],
                                    session=sess,
                                    dic=dataset.labels_dic)

                        summaries.evaluate(batch_x, batch_y, sess)
                        writer_train.add_run_metadata(run_metadata, 'step%d' % step)
                        writer_train.add_summary(summary_train, step)
                    else:
                        accuracy_train = cost_train = 0

                    ################### TESTING
                    if step % opts.testing_iterations == 0:
                        if opts.dataset_test:
                            batch_test_x, batch_test_y  = dataset_test.next_batch(batch_size=opts.batch_size)
                        else:
                            batch_test_x, batch_test_y  = dataset.next_batch(batch_size=opts.batch_size, testing=True)

                        accuracy_test, cost_test, summary_test = sess.run(
                            [summaries.accuracy, net.cost, merged ],
                            feed_dict={net.input: batch_test_x,net.labels: batch_test_y, net.keep_prob: 1.0})

                        if step % opts.STATS_STEP == 0:
                            embed_test.evaluate(
                                        batch_test_x[:opts.nb_embeddings,:],
                                        batch_test_y[:opts.nb_embeddings,:],
                                        session=sess,
                                        dic=dataset.labels_dic)
                        summaries.evaluate(batch_test_x, batch_test_y, sess)
                        writer_test.add_summary(summary_test, step)
                    else:
                        accuracy_test = cost_test = 0

                    App.log(0,  "\033[1;37m Step {0} - \033[0m {1:.2f} sec  | train -\033[32m acc {2:.3f}\033[0m cost {3:.3f} | test -\033[32m acc {4:.3f}\033[0m cost {5:.3f} |".format(
                                    step,
                                    time.time() - start_time,
                                    accuracy_train,
                                    cost_train,
                                    accuracy_test,
                                    cost_test,
                                     ))
