# -*- coding: utf-8 -*-
"""submission02_TimeSeriesPrediction.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-wZf5poABFyb4WVjjgkZXUA-taEMnDrt
"""

# Unduh dataset
!wget --no-check-certificate \
http://archive.ics.uci.edu/ml/machine-learning-databases/00235/household_power_consumption.zip\
 -O /tmp/household_power_consumption.zip

# Ekstraksi file zip
import zipfile,os

local_zip = '/tmp/household_power_consumption.zip'
zip_ref = zipfile.ZipFile(local_zip, 'r')
zip_ref.extractall('/tmp')
zip_ref.close()

# Siapkan dataset
import pandas as pd

df = pd.read_csv('/tmp/household_power_consumption.txt',
                 sep=';', 
                 parse_dates={'dates' : ['Date', 'Time']},  # Gabung kolom 'Date' dan 'Time'   
                 infer_datetime_format=True, 
                 low_memory=False, 
                 na_values=['nan','?'],  # Konversi string 'nan' dan '?' ke data numpy nan
                 index_col='dates')  # Konversi dataset ke time-series type

df

df.info()

df.isnull().sum()

df.columns

# Isi baris kosong/hilang 
import numpy as np

for column in df.columns:
    df[column].replace(0, np.nan, inplace=True)  # Isi dengan NAN
    df[column].fillna(method='ffill', inplace=True)  # Isi kembali dengan ffill method
    
df.isnull().any()

# Buat plot 
import matplotlib.pyplot as plt

# Plot rata-rata data per hari
for column in df.columns:
    mean = df[column].resample('d').mean()
    plt.plot(mean)
    plt.title(column, loc='center')
    plt.show()

df = df[['Global_active_power']]
df.tail()

df = df['2007-07-01 00:00:00':]  # Ambil data setelah tanggal 2007-07
df

plt.figure(figsize=(15, 5))
mean = df['Global_active_power'].resample('d').mean()
plt.plot(mean)
plt.title('Rata-rata Global_active_power per hari', loc='center')
plt.show()

# Resample dataset selama satu jam
df_resample = df.resample('h').mean() 
print('per-menit: ', df.shape[0])
print('per-jam: ', df_resample.shape[0])

df_resample

# Normalisasi data
from sklearn import preprocessing

values = df_resample.values.reshape(-1,1)
values = values.astype('float32')
scaler = preprocessing.MinMaxScaler(feature_range=(0, 1))
scaled = scaler.fit_transform(values)

values

scaled

# Bagi train set dan test set
train_size = int(len(scaled) * 0.79)
val_size = int(len(scaled) * 0.2)
test_size = len(scaled) - train_size - val_size
train, val, test = scaled[0:train_size,:], scaled[train_size:-(test_size),:], scaled[-(test_size):,:]
print(f'train: {len(train)}')
print(f'validation: {len(val)}')
print(f'test: {len(test)}')

from itertools import chain

train = np.array(list(chain.from_iterable(train)))
val = np.array(list(chain.from_iterable(val)))
test = np.array(list(chain.from_iterable(test)))

train

# Bagi sekuen data menjadi sample
def split_sequence(sequence, n_steps):
	X, Y = list(), list()
	for i in range(len(sequence)):
        # Cari bagian akhir dari pola sekuen
		end_iX = i + n_steps
        # Jika loop sudah berada di akhir
		if end_iX > len(sequence)-1:
			break
		# Gabungkan bagian input dan output dari pola sekuen
		seq_X, seq_Y = sequence[i:end_iX], sequence[end_iX]
		X.append(seq_X)
		Y.append(seq_Y)
	return np.array(X), np.array(Y)

# Bagi sekuen menjadi samples
n_steps = 12
train_X, train_Y = split_sequence(train, n_steps)
val_X, val_Y = split_sequence(val, n_steps)
test_X, test_Y = split_sequence(test, n_steps)

train_X

# reshape from [samples, timesteps] into [samples, timesteps, features]
n_features = 1
train_X = train_X.reshape((train_X.shape[0], train_X.shape[1], n_features))
val_X = val_X.reshape((val_X.shape[0], val_X.shape[1], n_features))
test_X = test_X.reshape((test_X.shape[0], test_X.shape[1], n_features))

# Buat arsitektur model
import tensorflow as tf
from keras.layers import LSTM

model = tf.keras.models.Sequential([
    tf.keras.layers.Bidirectional(LSTM(50), input_shape=(n_steps, n_features)),
    tf.keras.layers.Dense(30, activation='relu'),
    tf.keras.layers.Dense(10, activation='relu'),
    tf.keras.layers.Dense(1)
])

# Tentukan optimzer dan loss function model
optimizer = tf.keras.optimizers.Adam(lr=1.0e-03)
model.compile(optimizer=optimizer,
              loss=tf.keras.losses.Huber(),
              metrics=['mae'])

class myCallback(tf.keras.callbacks.Callback):
  def on_epoch_end(self, epoch, logs={}):
    if(logs.get('mae')<0.065 and logs.get('val_mae')<0.065):
      print("\nTraining sudah mencapai MAE < 6.5% skala data !!")
      self.model.stop_training = True

callbacks = myCallback()
reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.2,
                                                 patience=5, min_lr=1.0e-04)

# Latih model
history = model.fit(train_X, train_Y, 
                    epochs=100, batch_size=128, 
                    validation_data=(val_X, val_Y), 
                    verbose=2, callbacks=[callbacks,reduce_lr])

# Plot loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Training and Validation loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend(['Training', 'Validation'])
plt.show

# Buat prediksi dengan test_X set
y_hat = model.predict(test_X)
plt.figure(figsize=(10,5))
plt.plot(test_Y, label='true')
plt.plot(y_hat, label='predict')
plt.title('Test Prediction')
plt.legend()
plt.show()

# Balikkan skala nilai prdeiksi ke nilai semula
y_hat_inverse = scaler.inverse_transform(y_hat.reshape(-1, 1))
test_Y_inverse = scaler.inverse_transform(test_Y.reshape(-1, 1))

# Hitung skala data
min_value = df_resample.values.min()
max_value = df_resample.values.max()
data_scale = max_value - min_value
print('min_sum:', min_value)
print('max_sum:', max_value)
print(f'MAE < 10% skala data = {(0.1 * data_scale):.3f}')

# Hitung MAE
forecast = y_hat_inverse
actual = test_Y_inverse
errors = forecast - actual
mae = np.abs(errors).mean()
print(f'Test MAE: {mae:.2f}')
