from src.traceability_module.W_Trace_model import *
import argparse

# locating all wtrace related files
#wtrace_data_path = 'src/traceability_module/wtrace_data'
wtrace_data_path = 'wtrace_data'
# metric id fixed for extracting lat long from the user provided file format
metric_id = "6587929f-e425-498b-b450-aa615851400b"

class Watermarking_Correlation:
    # function to extract trip lat long from the raw input file
    def get_trip_lat_long(self, trips_data_dict):
        trip_id = trips_data_dict['trip_id']
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
        pdf_data_v = {'watermarked_lat': lst_lat, 'watermarked_long': lst_long, 'trip_timestamp': lst_trip_timestamps[0]}
        trip_df = pd.DataFrame(pdf_data_v, columns=['watermarked_lat', 'watermarked_long', 'trip_timestamp'])
        trip_df['trip_id'] = lst_trip_id[0]
        # saving only the coordinates data along with timestamp and trip_id
        # saving the trip file in form of dataframe
        trip_df.to_csv(wtrace_data_path + '/intermediate_files/' + trip_id + '_watermarked_lat_long.csv', index=False)
        return trip_df

    def get_watermark_correlation(self, trips_data_dict, watermark_file=None):
        # get the trip file with watermarked latitude and longitude
        trip_df = self.get_trip_lat_long(trips_data_dict)
        trip_id = trips_data_dict['trip_id']
        # load x1_fill of that trajectory
        x1_full = np.load(wtrace_data_path + '/intermediate_files/' + trip_id + '_x1_full.npy', allow_pickle=True)
        # load watermark file
        watermark_file = trip_id if watermark_file is None else watermark_file
        watermark = np.load(wtrace_data_path + '/intermediate_files/' + watermark_file + '_watermark.npy')

        cnt_slices = floor(len(trip_df) / 16)
        normal_slice_len = 16
        last_slice_len = len(trip_df) % 16
        pd.options.mode.chained_assignment = None
        appended_data, watermark_full, extracted_watermark_full = [], [], []
        for i in range(cnt_slices):
            current_watermark = watermark[normal_slice_len * i:normal_slice_len * i + normal_slice_len]
            watermark_full.append(current_watermark)
            df_1 = trip_df[normal_slice_len * i:normal_slice_len * i + normal_slice_len]
            df_1 = df_1.reset_index(drop=True)
            col_lat, col_long = 'watermarked_lat', 'watermarked_long'
            extract_wc = watermarkExtract(df_1, x1_full[i], normal_slice_len, col_lat, col_long)
            extracted_watermark_full.append(extract_wc)
            corr_watermark = ncc(np.array(extract_wc).flatten(), np.array(current_watermark).flatten())
            print(f"correlation. for sub-trajectory {i + 1} is {corr_watermark}")

        # remaining rows apart from those in multiple of the fixed normal slice
        last_watermark = watermark[normal_slice_len * cnt_slices:normal_slice_len * cnt_slices + last_slice_len]
        watermark_full.append(last_watermark)
        df_3 = trip_df[normal_slice_len * cnt_slices:normal_slice_len * cnt_slices + last_slice_len]
        df_3 = df_3.reset_index(drop=True)
        col_lat, col_long = 'watermarked_lat', 'watermarked_long'
        extract_wc = watermarkExtract(df_3, x1_full[cnt_slices], last_slice_len, col_lat, col_long)
        extracted_watermark_full.append(extract_wc)
        corr_watermark_last = ncc(np.array(extract_wc).flatten(), np.array(last_watermark).flatten())
        print('correlation for last remaining segment is:', corr_watermark_last)

        # correlation until remaining segment
        corr_watermark = ncc(np.array(watermark_full[:cnt_slices]), np.array(extracted_watermark_full[:cnt_slices]))

        final_corr = (corr_watermark * cnt_slices + corr_watermark_last) / (cnt_slices + 1)
        return final_corr

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--watermarked_trip_file', type=str, default=None,
                        help='name of watermarked trip file')
    parser.add_argument('--watermark_file', type=str, default=None,
                        help='name of watermarked trip file')
    args = parser.parse_args()

    trip_id = '881adde5-5f36-4952-915d-42e971ce8529'
    watermarked_trip_file = 'output_of_'+trip_id if args.watermarked_trip_file is None else args.watermarked_trip_file
    watermark_file = trip_id if args.watermark_file is None else args.watermark_file
    obj = Watermarking_Correlation()


    ## check correlation
    with open(wtrace_data_path + '/output_files/' + watermarked_trip_file + '.json', 'r') as f:
        trips_data_dict = json.load(f)
        trips_data_dict = trips_data_dict[0]
    final_corr = obj.get_watermark_correlation(trips_data_dict, watermark_file)

    # after all rows get processed, finding correlation of full trajectory's watermark
    print(f"\ncorrelation. for entire trajectory is {final_corr}")