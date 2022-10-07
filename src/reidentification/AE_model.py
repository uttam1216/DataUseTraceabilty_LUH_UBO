import tensorflow as tf


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