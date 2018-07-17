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
import json

'''
def build_command_from_conf(conf_file):
    try:
        with open(conf_file) as json_file:
            conf_data = json.load(json_file)
    except:
        App.log(0 , "There isn't any valide json file")
        return []

    build_cmd_line = []
    for key , value in conf_data.items():
        if is_primitive(value) or isinstance(value , int):
            build_cmd_line.append("--{}={}".format(key , value))
    return build_cmd_line
'''
'''
primitive_list = [str ,int ,float, bool]
def is_primitive(var):
    for primitive_var_type in primitive_list:
        if isinstance(var , primitive_var_type):
            return True
    return False
'''

def overwrite_conf_with_opts(conf_data , opts , default_values_dic):
    for key , value in default_values_dic.items():
        if key not in conf_data:
            conf_data[key] = value
    for key , value in opts.items():
        if value is not None or key not in conf_data:
            conf_data[key] = value

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
        help='Define output folder to store the neural network and trains.')

    parser.add_option("--dnn",
        action="store", type="string", dest="dnn",
        help='DNN model to train (Default: ).')
    ###
    parser.add_option("--training-iterations",
        action="store", type="int", dest="training_iters",
        help='Number of training iterations (Default: 20000 iterations).')

    parser.add_option("--testing-step",
        action="store", type="int", dest="testing_iterations",
        help='Number of training iterations between each testing step (Default: 10).')

    parser.add_option("--batchsize",
        action="store", type="int", dest="batch_size",
        help='Size of the training batch (Default:64).')

    parser.add_option("--expert-mode",
        action="store_true", dest="expert_mode" ,
        help='Are you training an expert like model ?')

    parser.add_option("--learning-rate",
        action="store", type="float", dest="learning_rate",
        help='Learning rate (default: 0.001).')
    ###
    parser.add_option("--stats-step",
        action="store", type="int", dest="STATS_STEP",
        help='Step period to compute statistics, embeddings and feature maps (Default: 10).')

    parser.add_option("--nb-embeddings",
        action="store", type="int", dest="nb_embeddings",
        help='Number of embeddings to compute (default: 50)..')
    ###
    parser.add_option("--job-type",
        action="store", type="string", dest="job_type",
        help='Selector the process job: ps or worker (default:worker).')

    parser.add_option("--task-index",
        action="store", type="int", dest="task_index",
        help='Provide the task index to execute (default:0).')

    parser.add_option("--workers",
        action="store", type="string", dest="workers",
        help='List of workers (worker1.mynet:2222,worker2.mynet:2222, etc).')

    parser.add_option("--ps",
        action="store", type="string", dest="ps",
        help='List of parameter servers (ps1.mynet:2222,ps2.mynet:2222, etc).')

    parser.add_option("--cutoff-up",
        action="store", type="string", dest="cutoff_up",
        help='Pixel cutoff on frequency axis high value.')

    parser.add_option("--cutoff-down",
        action="store", type="string", dest="cutoff_down",
        help='Pixel cutoff on frequency axis low value.')

    parser.add_option("--conf-file", action="store", type="string", dest="conf_file" ,
        default="" , help="json file holding the data necessary about class access path and type")
    ###

    default_values_dic = {"dataset_train" : "" ,"out" : "/tmp/tflearn_logs" , "dnn" : "default" , "training_iters" : 20000,"testing_iterations" : 10,
                            "batch_size" : 64, "learning_rate" : 0.001, "STATS_STEP" : 20, "nb_embeddings" : 50, "task_index" : 0, "workers" : "localhost:2222","ps": "",
                            "job_type" : "worker", "cutoff_down":20, "cutoff_up":170 , "expert_mode":False}

    (opts, args) = parser.parse_args()
    opts = vars(opts)

    try:
        with open(opts["conf_file"]) as json_file:
            conf_data = json.load(json_file)
    except:
        conf_data = dict()
        App.log(0 , "There isn't any valide json file")

    overwrite_conf_with_opts(conf_data , opts , default_values_dic)

    ###################################
    # Cluster configuration
    ###################################
    ps      = conf_data["ps"].split(",")
    workers = conf_data["workers"].split(",")
    cluster  = {"worker":workers}
    if ps[0] != "":
        cluster["ps"] = ps
    cluster = tf.train.ClusterSpec(cluster)

    # start a server for a specific task
    server = tf.train.Server(cluster,   job_name=conf_data["job_type"],
                                        task_index=conf_data["task_index"])

    if conf_data["job_type"] == "ps":
        App.log(0, "Parameter server " + ps[conf_data["task_index"]]+ " started.")
        server.join()
    elif conf_data["job_type"] != "worker":
        App.log(0, "Bad argument in job name [ps | worker]")
        sys.exit(0)

    App.log(0, "Worker " + workers[conf_data["task_index"]]+ " started")

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
    ###################################    '''
    dataset      = database.Dataset(conf_data["dataset_train"] , conf_data=conf_data)
    if conf_data["dataset_test"]:
        dataset_test = database.Dataset(conf_data["dataset_test"], class_file=conf_data)
    App.log(0, "Sample size: " + str(dataset.size[0]) + 'x' + str(dataset.size[1]))
    conf_data["size"]   = dataset.size

    ###################################
    # Between-graph replication
    ###################################
    with tf.device(tf.train.replica_device_setter(
        worker_device="/job:worker/task:%d" % conf_data["task_index"],
        cluster=cluster)):

        global_step  = tf.train.get_or_create_global_step()
        writer_train = tf.summary.FileWriter(conf_data["out"]+"/model/train/")
        writer_test  = tf.summary.FileWriter(conf_data["out"]+"/model/test/")

        ###################################
        # Build graphs
        ###################################
        App.log(0, "Loading DNN model from:  " + conf_data["dnn"])
        sys.path.append('./')
        exec("import "+os.path.dirname(conf_data["dnn"])+"."+os.path.basename(conf_data["dnn"]).replace(".py","")+" as model")
        net = eval("model.DNN([dataset.size[0], dataset.size[1]], dataset.get_nb_classes(), dataset.class_tree)")

        ## Generate summaries
        with tf.name_scope('Summaries'):
            summaries = vizu.Summaries(net, dataset.get_nb_classes())

            ## Construct filter images
            with tf.name_scope('Visualize_filters'):
                summaries.build_kernel_filters_summaries(net.show_kernel_map)

        with tf.variable_scope("embeddings"):
            conf_data["nb_embeddings"] = min(conf_data["nb_embeddings"], dataset.data.shape[0])
            proj      = projector.ProjectorConfig()
            embed_train     = vizu.Embedding("OUT_train", net.input, net.out, net.keep_prob, proj, conf_data["nb_embeddings"], conf_data["out"])
            embed_test      = vizu.Embedding("OUT_test",  net.input, net.out, net.keep_prob, proj, conf_data["nb_embeddings"], conf_data["out"])
            projector.visualize_embeddings(writer_test, proj)
            projector.visualize_embeddings(writer_train, proj)

        App.log(0, "Generate summaries graph.")
        merged = tf.summary.merge_all()

        with tf.name_scope('Trainer'):
            train_op = tf.train.AdagradOptimizer(conf_data["learning_rate"]).minimize(net.cost, global_step=global_step)
            hooks=[tf.train.StopAtStepHook(last_step=conf_data["training_iters"])]

        ###################################
        # Start the session
        ###################################
        if conf_data["task_index"] != 0:
            App.log(0, "Waiting for the master worker.")

        with tf.train.MonitoredTrainingSession(master=server.target,
                                               is_chief=(conf_data["task_index"] == 0),
                                               checkpoint_dir=conf_data["out"]+"/model/",
                                               hooks=hooks,
                                               config=config) as sess:
                App.ok(0, "Training is starting.")
                writer_train.add_graph(sess.graph)
                writer_test.add_graph(sess.graph)

                # Save the model and conf file
                shutil.copyfile(conf_data["dnn"], conf_data["out"] + "/model.py")
                with open(conf_data["out"] + "/conf.json", 'w') as outfile:
                    json.dump(conf_data, outfile)

                while not sess.should_stop():
                    App.log(0, "---")
                    start_time = time.time()

                    ################### TRAINING
                    batch_x, batch_y    = dataset.next_batch(batch_size=conf_data["batch_size"])

                    _, step = sess.run( [train_op, global_step],
                        feed_dict={ net.input: batch_x, net.labels: batch_y, net.keep_prob: 0.5})

                    if step % conf_data["STATS_STEP"] == 0:
                        run_options         = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
                        run_metadata        = tf.RunMetadata()

                        _, accuracy_train, cost_train, summary_train = sess.run(
                            [train_op, summaries.accuracy, net.cost, merged],
                            feed_dict={ net.input: batch_x, net.labels: batch_y, net.keep_prob: 0.25},
                            options=run_options, run_metadata=run_metadata)

                        embed_train.evaluate(
                                    batch_x[:conf_data["nb_embeddings"],:],
                                    batch_y[:conf_data["nb_embeddings"],:],
                                    session=sess,
                                    dic=dataset.conf_data["classes"])

                        summaries.evaluate(batch_x, batch_y, sess)
                        writer_train.add_run_metadata(run_metadata, 'step%d' % step)
                        writer_train.add_summary(summary_train, step)
                    else:
                        accuracy_train = cost_train = 0

                    ################### TESTING
                    if step % conf_data["testing_iterations"] == 0:
                        if conf_data["dataset_test"]:
                            batch_test_x, batch_test_y  = dataset_test.next_batch(batch_size=conf_data["batch_size"])
                        else:
                            batch_test_x, batch_test_y  = dataset.next_batch(batch_size=conf_data["batch_size"], testing=True)

                        accuracy_test, cost_test, summary_test = sess.run(
                            [summaries.accuracy, net.cost, merged ],
                            feed_dict={net.input: batch_test_x,net.labels: batch_test_y, net.keep_prob: 1.0})

                        if step % conf_data["STATS_STEP"] == 0:
                            embed_test.evaluate(
                                        batch_test_x[:conf_data["nb_embeddings"],:],
                                        batch_test_y[:conf_data["nb_embeddings"],:],
                                        session=sess,
                                        dic=dataset.conf_data["classes"])
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
