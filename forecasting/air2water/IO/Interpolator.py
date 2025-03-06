import pandas as pd
import numpy as np
import calendar
import os

class YearlyDataProcessor:
    def __init__(self, file_path, n_consecutive=7):
        self.df_orig = pd.DataFrame(file_path)
        self.n_consecutive = n_consecutive

    def interpolate_missing_data(self):
        df_na = self.df_orig.copy()
        df_na=pd.DataFrame(df_na)

        df_na.columns = ['year', 'month', 'day', 3, 4] + df_na.columns[5:].tolist()

        df_na[[3, 4]] = df_na[[3, 4]].applymap(lambda x: np.nan if isinstance(x, (int, float)) and x < -100 else x)
        df_na['date'] = pd.to_datetime(df_na[['year', 'month', 'day']])
        # Set 'date' as index and reindex to fill missing dates
        df_na.set_index('date', inplace=True)
        df = df_na.copy()
        date_range = pd.date_range(start=df.index.min(), end=df.index.max())
        df = df.reindex(date_range)
        # Keep the DatetimeIndex
        df['year'] = df.index.year
        df['month'] = df.index.month
        df['day'] = df.index.day
        temp=df[3]
        # Apply interpolation for column 3
        df[3] = self.DataInterpolator.interpolate(df_na[3], self.n_consecutive)
        df_na=df.copy()
        df_na[3]=temp
        return df, df_na

    class DataInterpolator:
        @staticmethod
        def interpolate(data: pd.Series, n_consecutive: int) -> pd.Series:
            interpolated_data = data.copy()
            indices = data.index
            for i in range(len(indices) - 1):
                prev_index = indices[i]
                next_index = indices[i + 1]
                gap_size = (next_index - prev_index).days - 1
                if gap_size == 0:
                    continue
                elif gap_size > n_consecutive:
                    climatology_values = YearlyDataProcessor.ClimatologyInterpolator.interpolate(data, prev_index, next_index)
                    interpolated_data = pd.concat([interpolated_data, climatology_values], axis=0)
                else:
                    linear_values = YearlyDataProcessor.LinearInterpolator.interpolate(data, prev_index, next_index)
                    interpolated_data = pd.concat([interpolated_data, linear_values], axis=0)
            return interpolated_data.sort_index()

    class LinearInterpolator:
        @staticmethod
        def interpolate(data: pd.Series, start: pd.Timestamp, end: pd.Timestamp):
            start_value = data.loc[start]
            end_value = data.loc[end]
            date_range = pd.date_range(start=start + pd.Timedelta(days=1), end=end - pd.Timedelta(days=1))
            interpolated_values = np.linspace(start_value, end_value, len(date_range) + 2)[1:-1]
            return pd.Series(data=interpolated_values, index=date_range)

    class ClimatologyInterpolator:
        @staticmethod
        def interpolate(data: pd.Series, start: pd.Timestamp, end: pd.Timestamp):
            date_range = pd.date_range(start=start + pd.Timedelta(days=1), end=end - pd.Timedelta(days=1))
            values = []
            for day in date_range:
                climatology_mean = data[(data.index.month == day.month) & (data.index.day == day.day)].mean()
                values.append(climatology_mean if pd.notna(climatology_mean) else 0.00)
            return pd.Series(data=values, index=date_range)

    def mean_year(self):
        df, df_na = self.interpolate_missing_data()

        missing_data_locations = df_na[df_na.isnull().any(axis=1)]
        missing_in_column_3 = df_na[df_na[3].isnull()]
        missing_in_column_3 = missing_in_column_3[['year', 'month', 'day']]
        numbermissingdata = missing_data_locations.shape[0]
        numbermissingcol3 = missing_in_column_3.shape[0]
        df_na['Interpolated'] = 0
        df_na.loc[missing_in_column_3.index, 'Interpolated'] = 1
        df['Interpolated']=df_na['Interpolated']
        df_na = df_na.reset_index().to_numpy()
        df = df.reset_index().to_numpy()
        df_na = df_na[:,1:]
        df = df[:,1:]
        missing_in_column_3 = missing_in_column_3.to_numpy()
        #df['interpolated']= df_na['interpolated']

        return df, numbermissingcol3, missing_in_column_3


if __name__ == "__main__":
    owd=os.getcwd()
    filepath = pd.read_csv('/home/dicam01/air2water_test/stndrck_sat_cc.csv',delimiter='\t',header=None)
    processor = YearlyDataProcessor(filepath)
    df, num_missing_col3, missing_col3 = processor.mean_year()
    print(df)
    print(num_missing_col3)
    print(missing_col3)
