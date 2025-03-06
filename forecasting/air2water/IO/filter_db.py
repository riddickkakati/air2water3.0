import os
import fnmatch
import pandas as pd
class CSVFilter:
    def __init__(self, input_file, output_file, threshold=float(3)):
        self.input_file = input_file
        self.output_file = output_file
        self.threshold = threshold

    def filter_csv(self):
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(self.input_file)

        # Filter rows based on the threshold condition
        filtered_df = df[df["like1"] < self.threshold]

        # Write the filtered DataFrame to a new CSV file
        filtered_df.to_csv(self.output_file, index=False)


# Example usage:
if __name__ == "__main__":
    input_file = "SCEUA_hymod"
    owd = os.getcwd()
    file2 = ''
    for file in os.listdir('.'):
        if fnmatch.fnmatch(file, f'{input_file}.csv'):
            file2 = file
    print(file2)
    input_file = str(owd + os.sep + file2)
    print(input_file)
    output_file = input_file[:-4] + str("_filtered.csv")
    csv_filter = CSVFilter(input_file, output_file)
    csv_filter.filter_csv()