from src.traceability_module.W_Trace_model import *
from requests import post
import argparse

# locating all wtrace related files
# wtrace_data_path = 'src/traceability_module/wtrace_data'
wtrace_data_path = 'wtrace_data'
# metric id fixed for extracting lat long from the user provided file format
metric_id = "6587929f-e425-498b-b450-aa615851400b"


class Watermark_Trajectory:
    def __init__(self):
        None

    # function to extract trip lat long from the raw input file
    def get_trip_lat_long(self, trips_data_dict, consent_id):
        trip_id = trips_data_dict['trip_id']
        try:
            with open(wtrace_data_path + '/input_files/' + consent_id + '_c$t_' + trip_id + '.json', 'w') as fp:
                json.dump(trips_data_dict, fp, indent=10)
                print('Input file saved successfully')
        except Exception as ex:
            print(ex)
        lst_trip_id, lst_trip_coords, lst_trip_timestamps = [], [], []
        lst_trip_id.append(trips_data_dict['trip_id'])
        trip_data_dict = trips_data_dict['data']
        for i in range(len(trip_data_dict)):
            # always same metric id to be used for getting GPS coordinates from the trip?
            if trip_data_dict[i]['metric_id'] == metric_id:
                lst_trip_coords.append(trip_data_dict[i]['values'])
                lst_trip_timestamps.append(trip_data_dict[i]['timestamps'])
        lst_lat, lst_long = [], []
        for item in lst_trip_coords[0]:
            lst_lat.append(item[0])
            lst_long.append(item[-1])
        pdf_data_v = {'latitude': lst_lat, 'longitude': lst_long, 'trip_timestamp': lst_trip_timestamps[0]}
        trip_df = pd.DataFrame(pdf_data_v, columns=['latitude', 'longitude', 'trip_timestamp'])
        trip_df['trip_id'] = lst_trip_id[0]
        # saving only the coordinates data along with timestamp and trip_id
        # saving the trip file in form of dataframe
        trip_df.to_csv(wtrace_data_path + '/intermediate_files/' + consent_id + '_c$t_' + trip_id + '_lat_long.csv', index=False)

        return trip_df

    # function to save watermarked df and its related statistics
    def save_watermarked_df(self, watermarked_df, trip_id, consent_id, cnt_slices, corr_watermark_last, watermark_full,
                            extracted_watermark_full):
        watermarked_df = watermarked_df.reset_index(drop=True)
        watermarked_df.to_csv(wtrace_data_path + '/intermediate_files/' + consent_id + '_c$t_' + trip_id + '_watermarkedTraj.csv', index=False)
        corr_watermark = ncc(np.array(watermark_full[:cnt_slices]), np.array(extracted_watermark_full[:cnt_slices]))
        final_corr = (corr_watermark * cnt_slices + corr_watermark_last) / (cnt_slices + 1)
        avg = watermarked_df["dist"].mean()
        max1 = watermarked_df["dist"].max()
        min1 = watermarked_df["dist"].min()
        # saving the file showing correlation
        if os.path.isfile(wtrace_data_path + '/' + 'tripwise_watermark_corrWithDistance.csv'):
            watermark_corrWithDistance_df = pd.read_csv(
                wtrace_data_path + '/' + 'tripwise_watermark_corrWithDistance.csv')
            df2 = {'trip_id': trip_id, 'mean_dist': "{0:0.4f}".format(avg), 'min_dist': "{0:0.4f}".format(min1),
                   'max_dist': "{0:0.4f}".format(max1), 'watermark_corr': "{0:0.4f}".format(final_corr)}
            watermark_corrWithDistance_df = watermark_corrWithDistance_df.append(df2, ignore_index=True)
            watermark_corrWithDistance_df.to_csv(wtrace_data_path + '/' + 'tripwise_watermark_corrWithDistance.csv',
                                                 index=False)
        else:
            # create a pandas dataframe for training dataset and save
            pdf_data_v = {'trip_id': [trip_id], 'mean_dist': ["{0:0.4f}".format(avg)],
                          'min_dist': ["{0:0.4f}".format(min1)],
                          'max_dist': ["{0:0.4f}".format(max1)], 'watermark_corr': ["{0:0.4f}".format(final_corr)]}
            watermark_corrWithDistance_df = pd.DataFrame(pdf_data_v,
                                                         columns=['trip_id', 'mean_dist', 'min_dist', 'max_dist',
                                                                  'watermark_corr'])
            watermark_corrWithDistance_df.to_csv(wtrace_data_path + '/' + 'tripwise_watermark_corrWithDistance.csv',
                                                 index=False)

    # function to save the image of original vs watermarked trajectory
    def save_trajectories(self, watermarked_df, path_to_trajectories_image):
        lst_orig_coords = watermarked_df[['latitude', 'longitude']].values.tolist()
        lst_watermarked_coords = watermarked_df[['watermarked_lat', 'watermarked_long']].values.tolist()
        # lst_orig_coords is a list of lat long pairs = watermarked_df[['latitude','longitude']].values.tolist()
        xs, ys = zip(*lst_orig_coords)
        plt.figure()
        plt.plot(xs, ys, c="blue", label="original")
        w_xs, w_ys = zip(*lst_watermarked_coords)
        plt.plot(w_xs, w_ys, c="red", label="watermarked")
        plt.rcParams["figure.figsize"] = (30, 30)
        plt.rcParams.update({'font.size': 22})
        plt.legend(loc="upper left")
        # first save the plots as image and then show...vice-versa does not work
        plt.savefig(path_to_trajectories_image)
        plt.show()

    # function to watermark the original trajectory
    def watermark_trajectory(self, trips_data_dict, consent_id=None):
        trip_df = self.get_trip_lat_long(trips_data_dict, consent_id)
        filterdata = trip_df.reset_index(drop=True)
        trip_idSeries = filterdata['trip_id'].unique()
        trip_id = trip_idSeries[0]
        print('trip_id is: ',trip_id)
        i = 0
        start = time.time()
        for trip_id in trip_idSeries:
            df_1 = filterdata.loc[filterdata['trip_id'] == trip_id]
            df_1 = df_1.reset_index(drop=True)
            cnt_slices = floor(len(df_1) / 16)
            normal_slice_len = 16
            last_slice_len = len(df_1) % 16
            l, m, n = floor(len(df_1) / 3), floor(len(df_1) / 3) + (len(df_1) % 3), floor(len(df_1) / 3)
            watermark = np.array([1] * l + [0] * m + [-1] * n)
            if len(df_1) != len(watermark):
                needed_pad = len(df_1) - len(watermark)
                watermark = np.append(watermark, [0 for i in range(needed_pad)])
            np.random.shuffle(watermark)
            np.save(wtrace_data_path + '/intermediate_files/watermark_files/' + consent_id + '_c$t_' + trip_id + '_watermark.npy', watermark)  # saving watermark file locally
            # start of change done on 4th Nov by Uttam to send watermarking secret file to central manager component
            y = open(wtrace_data_path + '/intermediate_files/watermark_files/' + consent_id + '_c$t_' + trip_id + '_watermark.npy', 'rb')
            files = {'file': y}
            from requests import post
            temp_url = 'http://localhost:5002'
            x = post(url=f'{temp_url}/wm_file', files=files).json()
            # end of change done on 4th Nov by Uttam to send watermarking secret file to central manager component


            pd.options.mode.chained_assignment = None
            appended_data, watermark_full, extracted_watermark_full, x1_full = [], [], [], []
            for i in range(cnt_slices):
                current_watermark = watermark[normal_slice_len * i:normal_slice_len * i + normal_slice_len]
                watermark_full.append(current_watermark)
                df_2 = df_1[normal_slice_len * i:normal_slice_len * i + normal_slice_len]
                df_2 = df_2.reset_index(drop=True)
                df_wc, x1 = addwatermark(current_watermark, df_2, normal_slice_len)
                x1_full.append(x1)
                df_wc['dist'] = df_wc.apply(lambda row: haversine(row['watermarked_long'], row['watermarked_lat'],
                                                                  row['longitude'], row['latitude']), axis=1)
                appended_data.append(df_wc)
                col_lat, col_long = 'watermarked_lat', 'watermarked_long'
                extract_wc = watermarkExtract(df_wc, x1, normal_slice_len, col_lat, col_long)
                extracted_watermark_full.append(extract_wc)
                corr_watermark = ncc(np.array(extract_wc).flatten(), np.array(current_watermark).flatten())

            # Remaining part start
            # remaining rows apart from those in multiple of the fixed normal slice
            last_watermark = watermark[normal_slice_len * cnt_slices:normal_slice_len * cnt_slices + last_slice_len]
            watermark_full.append(last_watermark)
            df_3 = df_1[normal_slice_len * cnt_slices:normal_slice_len * cnt_slices + last_slice_len]
            df_3 = df_3.reset_index(drop=True)
            df_wc, x1 = addwatermark(last_watermark, df_3, last_slice_len)
            x1_full.append(x1)
            df_wc['dist'] = df_wc.apply(lambda row: haversine(row['watermarked_long'], row['watermarked_lat'],
                                                              row['longitude'], row['latitude']), axis=1)
            appended_data.append(df_wc)
            extract_wc = watermarkExtract(df_wc, x1, last_slice_len, col_lat, col_long)
            extracted_watermark_full.append(extract_wc)
            corr_watermark_last = ncc(np.array(extract_wc).flatten(), np.array(last_watermark).flatten())
            # Remaining part end

            # after all rows get processed, save the watermarked df and its related statistics
            watermarked_df = pd.concat(appended_data)
            self.save_watermarked_df(watermarked_df, trip_id, consent_id, cnt_slices, corr_watermark_last, watermark_full,
                                     extracted_watermark_full)

        elapsed_time_fl = (time.time() - start)
        print('\n Time taken to do the watermarking in seconds: ', round(elapsed_time_fl, 2))

        # saving original extract of lat,long's fft for later to find correlation of watermarked trajectory wrt original
        np.save(wtrace_data_path + '/intermediate_files/extract_files/' + consent_id + '_c$t_' + trip_id + '_x1_full.npy', x1_full)
        y = open(wtrace_data_path + '/intermediate_files/extract_files/' + consent_id + '_c$t_' + trip_id + '_x1_full.npy', 'rb')
        files = {'file': y}
        # following url to be changed to point central server once deployment of manager component is done on it
        temp_url = 'http://localhost:5002'
        x = post(url=f'{temp_url}/wm_file', files=files).json()

        # write back the watermarked trajectory to original input file format
        prepare_output_trip_file(wtrace_data_path + '/input_files/' + consent_id + '_c$t_' + trip_id + '.json',
                                 wtrace_data_path + '/output_files/output_of_' + consent_id + '_c$t_' + trip_id + '.json', watermarked_df)
        try:
            with open(wtrace_data_path + '/output_files/output_of_' + consent_id + '_c$t_' + trip_id + '.json', 'r') as f:
                 watermarked_response = json.load(f)
        except:
            watermarked_response = None

        # saving the original vs watermarked trajectories image
        path_to_trajectories_image = wtrace_data_path + '/intermediate_files/' + consent_id + '_c$t_' + trip_id + '_orig_vs_wat_traj.png'
        self.save_trajectories(watermarked_df, path_to_trajectories_image)
        return watermarked_response


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trip_file', type=str, default='881adde5-5f36-4952-915d-42e971ce8529',
                        help='name of trip file')
    args = parser.parse_args()
    trip_id = '881adde5-5f36-4952-915d-42e971ce8529'
    input_trip_file = trip_id if args.trip_file is None else args.trip_file
    obj = Watermark_Trajectory()
    with open(wtrace_data_path + '/input_files/' + input_trip_file + '.json', 'r') as f:
        trips_data_dict = json.load(f)
        trips_data_dict = trips_data_dict[0]
    watermarked_response = obj.watermark_trajectory(trips_data_dict)
