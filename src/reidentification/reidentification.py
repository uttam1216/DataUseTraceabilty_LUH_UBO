from AE_model import AE
from joblib import load
import numpy as np
from dtw import *
from heapq import nsmallest


class Reidentification:
    # Set parameters AE
    batch_size = 256
    latent_dim = 50
    regulation_factor = 0.1
    feats_len = 3
    timesteps = 256

    # Hyperparameters
    preselection_amount = 2
    min_k = 2

    ae_model = None
    clf = None

    middle_point = np.array([41.149238, -8.611987, 0])


    def __init__(self):
        self.ae_model = AE(self.batch_size, self.timesteps, self.feats_len, latent_dim=self.latent_dim, regulation_factor=self.regulation_factor)
        self.ae_model.load_weights('./saved_model/1000e_checkpoint')
        self.clf = load('./saved_model/classifier.joblib')


    def re_identify_data(self, own_data, trajectory):
        # Subtrackt the middlepoint
        middlepoint_mat = np.tile(self.middle_point, (own_data.shape[0], 256, 1))
        own_set_m = own_data - middlepoint_mat
        own_set_m = own_set_m.astype(np.float32)

        middlepoint_mat = np.tile(self.middle_point, (256, 1))
        trj_m = trajectory - middlepoint_mat
        trj_m = trj_m.astype(np.float32)

        # Calculate the Representations of own_data
        s_own_set, rec_own_set = self.ae_model.run_model(own_set_m)
        s_own_set = s_own_set.numpy()

        s, _ = self.ae_model.run_model(np.expand_dims(trj_m, axis=0))

        ## Candidate Selection
        preselected_indices = self.__min_k_indices(s_own_set, s, self.preselection_amount)

        # Use min k distances
        distances = self.__trace_distance(s_own_set, s)[preselected_indices]
        ae_dist = distances[:self.min_k]

        ## Feature Extraction
        # get lowest distances of DTW
        preselected_vecs = own_set_m[preselected_indices]
        dwt_dist = self.__min_k_distance_DTW(preselected_vecs, trj_m, self.min_k)


        # Concatenate distances of AE and DTW
        dist = np.concatenate((ae_dist, dwt_dist), axis=0)

        ## Classification
        prediction = self.clf.predict(np.expand_dims(dist, axis=0))

        return prediction

    def __trace_distance(self, trace_encodings, trace_to_compare):
        """
        Given a list of encodings, compare them to a known encoding and get a euclidean distance
        for each comparison. The distance tells you how similar the encodings are.
        :param trace_encodings: List of encodings to compare
        :param trace_to_compare: A trace encoding to compare against
        :return: A numpy ndarray with the distance for each trace in the same order as the 'traces' array
        """
        if len(trace_encodings) == 0:
            return np.empty((0))

        return np.linalg.norm(trace_encodings - trace_to_compare, axis=1)

    def __min_k_distance_DTW(self, known_traces, trace_to_check, k):
        dist_list = []
        for t in known_traces:
            dist_list.append(dtw(t, trace_to_check).normalizedDistance)
        return nsmallest(k, dist_list)

    def __min_k_indices(self, trace_encodings, trace_to_compare, k):
        distances = self.__trace_distance(trace_encodings, trace_to_compare)
        indices = np.argpartition(distances, k)[:k]
        return indices

