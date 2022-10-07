from src.reidentification.reidentification import Reidentification
import numpy as np
import random


if __name__ == '__main__':
    exp_data_path = './saved_model'
    #exp_data_name = 'hannover'

    # Load Data
    own_set = np.load(exp_data_path + '/' + 'own_set.npy')
    total_set_labels = np.load(exp_data_path + '/' + 'labels.npy')
    #set_description = np.load(exp_data_path + '/' + exp_data_name + '_set_description.npy')
    total_set = np.load(exp_data_path + '/'  + 'test_data.npy')

    # Use random trace from test set
    n = random.randint(0,total_set.shape[0])

    trace = total_set[n]
    label = total_set_labels[n]

    # Create model
    reidentification_model = Reidentification()

    pred = reidentification_model.re_identify_data(own_set, trace)
    print("Used {}th entry.".format(n))
    print("Predicted result: {}".format(pred))
    print("True Label: {}".format(label))
