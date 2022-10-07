from joblib import load
import numpy as np
from dtw import *
from heapq import nsmallest
import tensorflow as tf

class AGE_Trace_reidentification:
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


    # This method runs AGE-Trace model to obtain the trajectory representation and returns it
    def get_trajectory_representation(self, trajectory):
        middlepoint_mat = np.tile(self.middle_point, (256, 1))
        trj_m = trajectory - middlepoint_mat
        s, _ = self.ae_model.run_model(np.expand_dims(trj_m, axis=0))
        return s


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

# Definition of Model
class AE(tf.keras.Model):
    def __init__(self, batch_size, timesteps, feats_size, latent_dim=50, regulation_factor=0.1):
        super(AE, self).__init__()
        self.latent_dim = latent_dim

        self._batch_size = batch_size
        self._timesteps = timesteps
        self._feats_size = feats_size
        self.regulation_factor = regulation_factor

        self.encoder = tf.keras.Sequential(
            [
                # Input data shape: (batch_size, 256, 3)
                tf.keras.layers.InputLayer(input_shape=(self._timesteps, self._feats_size)),
                tf.keras.layers.Flatten(),
                tf.keras.layers.Dense(units=self._timesteps * self._feats_size, activation=tf.nn.relu),
                # tf.keras.layers.Dense(units= self._timesteps * self._feats_size, activation=tf.nn.relu),
                # No activation
                tf.keras.layers.Dense(latent_dim, kernel_regularizer='l2'),

            ]
        )

        self.decoder = tf.keras.Sequential(
            [
                tf.keras.layers.InputLayer(input_shape=(latent_dim,)),
                tf.keras.layers.Dense(units=self._timesteps * self._feats_size, activation=tf.nn.relu),
                tf.keras.layers.Dense(units=self._timesteps * self._feats_size, activation=None),
                tf.keras.layers.Reshape(target_shape=(self._timesteps, self._feats_size)),
            ]
        )

    def run_model(self, x):
        s = self.encoder(x)
        x_recon = self.decoder(s)
        return s, x_recon

    def compute_loss(self, x, y):
        s, x_recon = self.run_model(x)
        # Simple Squered Diff
        cost = tf.math.reduce_mean(tf.square(tf.subtract(x_recon, y)))

        reg_loss = self.regulation_factor * tf.math.reduce_sum(model.encoder.losses)
        return cost + reg_loss

    # Training and Test Step
    @tf.function
    def train_step(self, x, y, optimizer):
        """Executes one training step and returns the loss.

        This function computes the loss and gradients, and uses the latter to
        update the model's parameters.
        """
        with tf.GradientTape() as tape:
            loss = self.compute_loss(x, y)
        gradients = tape.gradient(loss, self.trainable_variables)
        optimizer.apply_gradients(zip(gradients, self.trainable_variables))
        return loss

    @tf.function
    def test_step(self, x):
        # training=False is only needed if there are layers with different
        # behavior during training versus inference (e.g. Dropout).

        t_loss = self.compute_loss(x, x)
        return t_loss