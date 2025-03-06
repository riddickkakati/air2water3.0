import numpy as np
import pandas as pd
from datetime import datetime
from django.conf import settings
import os
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
import tensorflow as tf
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from catboost import CatBoostRegressor
from sklearn.model_selection import KFold
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.decomposition import KernelPCA
import zipfile
import time
import shutil



def interpolate_missing_data(self, df_orig):
    """Interpolate missing data in the dataset"""
    df_na = df_orig.copy()
    df_na = pd.DataFrame(df_na)

    df_na.columns = ['year', 'month', 'day', 3, 4] + df_na.columns[5:].tolist()

    # Handle missing values
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
    temp = df[3]

    # Apply interpolation for column 3
    df[3] = DataInterpolator.interpolate(df_na[3], self.n_data_interpolate)
    df_na = df.copy()
    df_na[3] = temp

    return df, df_na


def process_yearly_data(self, df_orig):
    """Process yearly data including interpolation"""
    df, df_na = self.interpolate_missing_data(df_orig)

    # Find missing data locations
    missing_data_locations = df_na[df_na.isnull().any(axis=1)]
    missing_in_column_3 = df_na[df_na[3].isnull()]
    missing_in_column_3 = missing_in_column_3[['year', 'month', 'day']]
    numbermissingdata = missing_data_locations.shape[0]
    numbermissingcol3 = missing_in_column_3.shape[0]

    # Add interpolation flag
    df_na['Interpolated'] = 0
    df_na.loc[missing_in_column_3.index, 'Interpolated'] = 1
    df['Interpolated'] = df_na['Interpolated']

    # Reset index and convert to numpy
    df_na = df_na.reset_index().to_numpy()
    df = df.reset_index().to_numpy()
    df_na = df_na[:, 1:]
    df = df[:, 1:]
    missing_in_column_3 = missing_in_column_3.to_numpy()

    return df, numbermissingcol3, missing_in_column_3


class YearlyDataProcessor:
    def __init__(self, file_path, n_consecutive=7):
        self.df_orig = pd.DataFrame(file_path)
        self.n_consecutive = n_consecutive

    def interpolate_missing_data(self):
        df_na = self.df_orig.copy()
        df_na = pd.DataFrame(df_na)

        df_na.columns = ['year', 'month', 'day', 3, 4] + df_na.columns[5:].tolist()

        # Handle missing values for both columns 3 and 4
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

        # Store original values before interpolation
        temp3 = df[3].copy()
        temp4 = df[4].copy()

        # Apply interpolation for both columns
        df[3] = self.DataInterpolator.interpolate(df_na[3], self.n_consecutive)
        df[4] = self.DataInterpolator.interpolate(df_na[4], self.n_consecutive)

        df_na = df.copy()
        df_na[3] = temp3
        df_na[4] = temp4

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
                    climatology_values = YearlyDataProcessor.ClimatologyInterpolator.interpolate(data, prev_index,
                                                                                                 next_index)
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
        missing_in_columns = df_na[df_na[[3, 4]].isnull().any(axis=1)]
        missing_in_columns = missing_in_columns[['year', 'month', 'day']]
        numbermissingdata = missing_data_locations.shape[0]
        numbermissingcols = missing_in_columns.shape[0]

        df_na['Interpolated'] = 0
        df_na.loc[missing_in_columns.index, 'Interpolated'] = 1
        df['Interpolated'] = df_na['Interpolated']

        df_na = df_na.reset_index().to_numpy()
        df = df.reset_index().to_numpy()
        df_na = df_na[:, 1:]  # Remove the index column
        df = df[:, 1:]  # Remove the index column
        missing_in_columns = missing_in_columns.to_numpy()

        return df, numbermissingcols, missing_in_columns


class ML_Model:
    def __init__(self, user_id=0, group_id=0, interpolate=True, n_data_interpolate=7,
                 validation_required=False, percent=10,
                 model="air2water",
                 missing_data_threshold=30, interpolate_use_rmse=True,
                 air2waterusercalibrationpath=None,
                 air2streamusercalibrationpath=None,
                 air2wateruservalidationpath=None,
                 air2streamuservalidationpath=None,
                 results_file_name="results.db",
                 email_send=0, sim_id=0, email_list=None):

        self.user_id = user_id
        self.group_id = group_id
        self.model = model
        self.interpolate = interpolate
        self.n_data_interpolate = n_data_interpolate
        self.missing_data_threshold = missing_data_threshold
        self.interpolate_use_rmse = interpolate_use_rmse
        self.validation_required = validation_required
        self.percent = percent
        self.air2waterusercalibrationpath = air2waterusercalibrationpath
        self.air2streamusercalibrationpath = air2streamusercalibrationpath
        self.air2wateruservalidationpath = air2wateruservalidationpath
        self.air2streamuservalidationpath = air2streamuservalidationpath
        self.results_file_name = results_file_name
        self.sim_id = sim_id
        self.email_send = email_send
        self.email_list = email_list if email_list else []
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.kpca = KernelPCA(n_components=2, kernel='rbf')
        self.lda = LDA(n_components=2)
        self.owd = settings.MEDIA_ROOT


    def datetimecalc(self, dfinput):
        """Calculate datetime and normalized day of year from input data"""
        Y = dfinput[:, 0]
        M = dfinput[:, 1]
        D = dfinput[:, 2]
        date = [datetime(int(y), int(m), int(d)) for y, m, d in zip(Y, M, D)]
        return date, np.asarray([d.timetuple().tm_yday / 366 for d in date])

    def prepare_ml_data(self, data, is_air2stream=False):
        """
        Prepare data for machine learning by creating feature set and target variable
        """
        # Remove rows where target variable (column 4) is -999
        valid_indices = data[:, 4] != -999
        filtered_data = data[valid_indices]

        # Calculate dates and tt for the filtered data
        dates, tt = self.datetimecalc(filtered_data)

        if is_air2stream:
            # For air2stream: Features = [tt, column4, column6], Target = column5
            X = np.column_stack((tt, filtered_data[:, 3], filtered_data[:, 5]))  # Features
            y = filtered_data[:, 4]  # Target
        else:
            # For air2water: Features = [tt, column4], Target = column5
            X = np.column_stack((tt, filtered_data[:, 3]))  # Features
            y = filtered_data[:, 4]  # Target

        return {
            'X': X,
            'y': y,
            'dates': dates,
            'original_data': filtered_data
        }

    def discretize_target(self, y_train, y_val, n_bins=5):
        """
        Discretize continuous target variable into classes for LDA

        Parameters:
        y_train: Training target values
        y_val: Validation target values
        n_bins: Number of bins for discretization

        Returns:
        y_train_discrete: Discretized training targets
        y_val_discrete: Discretized validation targets
        """
        # Initialize the discretizer
        discretizer = KBinsDiscretizer(n_bins=n_bins, encode='ordinal', strategy='quantile')

        # Reshape for sklearn
        y_train_reshaped = np.array(y_train).reshape(-1, 1)
        y_val_reshaped = np.array(y_val).reshape(-1, 1)

        # Fit and transform training data
        y_train_discrete = discretizer.fit_transform(y_train_reshaped)

        # Transform validation data using the same bins
        y_val_discrete = discretizer.transform(y_val_reshaped)

        return y_train_discrete.ravel().astype(int), y_val_discrete.ravel().astype(int)

    def save_results_csv(self, predictions, data, mode, owd):
        """Save results to CSV in the required format"""
        dates_str = [d.strftime('%Y-%m-%d') for d in data['dates']]
        df = pd.DataFrame({
            'Date': dates_str,
            'Air_temperature_data': data['original_data'][:, 3],
            'Best_simulation': predictions,
            'Evaluation_(Water_temperature_data)': data['y']
        })

        ######REMOVE OWD AND OSMAKEDIRS PART

        results_dir = f"{owd}/ml_results/{self.user_id}_{self.group_id}/"
        os.makedirs(results_dir, exist_ok=True)
        filepath = f"{results_dir}results_{self.sim_id}_{mode}.csv"
        df.to_csv(filepath, index=False)
        return df

    def plot_results(self, df, mode, owd, train, mean=None, std=None):
        """Create time series plot in the required format with R² score"""
        fig, ax = plt.subplots(figsize=(12, 6))

        df = df.sort_values('Date')

        dates = pd.to_datetime(df['Date'])

        ax.plot(
            dates,
            df['Best_simulation'],
            color="black",
            linestyle="solid",
            label="Simulated water temperature"
        )
        ax.plot(
            dates,
            df['Evaluation_(Water_temperature_data)'],
            "r.",
            markersize=3,
            label="Observed water temperature data"
        )
        ax.plot(
            dates,
            df['Air_temperature_data'],
            color="blue",
            linewidth=0.2,
            label="Observed air temperature data"
        )

        if train == "calib":
            # Calculate R² score
            r2 = f"{mean:.3f} ± {std:.3f}"

            # Add R² score to plot
            plt.text(0.02, 0.98, f'R² = {r2}',
                     transform=ax.transAxes,
                     bbox=dict(facecolor='white', alpha=0.8),
                     verticalalignment='top')
        elif train== "valid":
            # Calculate R² score
            r2 = r2_score(df['Evaluation_(Water_temperature_data)'], df['Best_simulation'])

            # Add R² score to plot
            plt.text(0.02, 0.98, f'R² = {r2:.3f}',
                     transform=ax.transAxes,
                     bbox=dict(facecolor='white', alpha=0.8),
                     verticalalignment='top')

        plt.xlabel("Year")
        plt.ylabel("Temperature")
        plt.legend(loc="upper right")

        filepath = f"{owd}/ml_results/{self.user_id}_{self.group_id}/{mode}_best_modelrun_{self.sim_id}.png"
        fig.savefig(filepath, dpi=100)
        plt.close()

        return filepath

    def train_svr(self, X_train, y_train, X_val, y_val):
        """Train SVR model and make predictions"""
        # Initialize SVR with RBF kernel
        regressor = SVR(kernel='rbf')

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_mlr(self, X_train, y_train, X_val, y_val):
        """Train Multiple Linear Regression model and make predictions"""
        # Initialize Linear Regression
        regressor = LinearRegression()

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """Train XGBoost model and make predictions"""
        from xgboost import XGBRegressor

        # Initialize XGBoost regressor with enable_categorical=False
        regressor = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            enable_categorical=False  # Add this parameter
        )

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_random_forest(self, X_train, y_train, X_val, y_val):
        """Train Random Forest model and make predictions"""


        # Initialize Random Forest regressor
        regressor = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_decision_tree(self, X_train, y_train, X_val, y_val):
        """Train Decision Tree model and make predictions"""


        # Initialize Decision Tree regressor
        regressor = DecisionTreeRegressor(
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_catboost(self, X_train, y_train, X_val, y_val):
        """Train CatBoost model and make predictions"""


        # Initialize CatBoost regressor
        regressor = CatBoostRegressor(
            iterations=100,
            learning_rate=0.1,
            depth=6,
            verbose=False
        )

        # Train the model
        regressor.fit(X_train, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train)
        val_pred = regressor.predict(X_val)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_polynomial(self, X_train, y_train, X_val, y_val, degree=2):
        """Train Polynomial Regression model and make predictions"""
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.linear_model import LinearRegression

        # Create polynomial features
        poly_features = PolynomialFeatures(degree=degree)
        X_train_poly = poly_features.fit_transform(X_train)
        X_val_poly = poly_features.transform(X_val)

        # Initialize and train the model
        regressor = LinearRegression()
        regressor.fit(X_train_poly, y_train)

        # Make predictions
        train_pred = regressor.predict(X_train_poly)
        val_pred = regressor.predict(X_val_poly)

        # Perform k-fold cross validation
        cv_scores = cross_val_score(regressor, X_train_poly, y_train, cv=10)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def train_ann(self, X_train, y_train, X_val, y_val):
        """Train Artificial Neural Network model and make predictions"""
        # Convert inputs to float32
        X_train = np.asarray(X_train).astype(np.float32)
        y_train = np.asarray(y_train).astype(np.float32)
        X_val = np.asarray(X_val).astype(np.float32)
        y_val = np.asarray(y_val).astype(np.float32)

        # Create the ANN model
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(32, activation='relu', input_shape=(X_train.shape[1],)),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)
        ])

        # Compile the model
        model.compile(optimizer='adam', loss='mean_squared_error')

        # Train the model
        model.fit(X_train, y_train, epochs=100, batch_size=32, verbose=0)

        # Make predictions
        train_pred = model.predict(X_train).flatten()
        val_pred = model.predict(X_val).flatten()

        # For cross-validation with Keras, we'll use a custom implementation
        def get_cv_scores(X, y, n_splits=10):
            kf = KFold(n_splits=n_splits)
            scores = []

            # Convert inputs to float32
            X = np.asarray(X).astype(np.float32)
            y = np.asarray(y).astype(np.float32)

            for train_idx, val_idx in kf.split(X):
                X_t, X_v = X[train_idx], X[val_idx]
                y_t, y_v = y[train_idx], y[val_idx]

                model = tf.keras.Sequential([
                    tf.keras.layers.Dense(32, activation='relu', input_shape=(X.shape[1],)),
                    tf.keras.layers.Dense(16, activation='relu'),
                    tf.keras.layers.Dense(1)
                ])
                model.compile(optimizer='adam', loss='mean_squared_error')
                model.fit(X_t, y_t, epochs=100, batch_size=32, verbose=0)

                y_pred = model.predict(X_v).flatten()
                scores.append(r2_score(y_v, y_pred))

            return np.array(scores)

        # Get cross-validation scores
        cv_scores = get_cv_scores(X_train, y_train)

        return {
            'train_pred': train_pred,
            'val_pred': val_pred,
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }

    def perform_grid_search(self, X_train, y_train, X_val, y_val):
        """Perform grid search for all ML algorithms"""
        from sklearn.model_selection import GridSearchCV
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend

        # Dictionary to store best parameters and scores
        grid_search_results = {}

        # SVR parameters
        try:
            print("Performing grid search for SVR...")
            svr_params = {
                'C': [0.1, 1, 10],
                'kernel': ['rbf', 'linear'],
                'gamma': ['scale', 'auto'],
                'epsilon': [0.1, 0.2]
            }
            svr = SVR()
            svr_grid = GridSearchCV(svr, svr_params, cv=5, n_jobs=1, scoring='r2')  # Using n_jobs=1
            svr_grid.fit(X_train, y_train)
            grid_search_results['SVR'] = {
                'best_params': svr_grid.best_params_,
                'best_score': svr_grid.best_score_,
                'validation_score': svr_grid.score(X_val, y_val)
            }
        except Exception as e:
            print(f"Error in SVR grid search: {str(e)}")
            grid_search_results['SVR'] = {'error': str(e)}

        # Random Forest parameters
        try:
            print("Performing grid search for Random Forest...")
            rf_params = {
                'n_estimators': [100, 200],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2]
            }
            rf = RandomForestRegressor(random_state=42)
            rf_grid = GridSearchCV(rf, rf_params, cv=5, n_jobs=1, scoring='r2')  # Using n_jobs=1
            rf_grid.fit(X_train, y_train)
            grid_search_results['RandomForest'] = {
                'best_params': rf_grid.best_params_,
                'best_score': rf_grid.best_score_,
                'validation_score': rf_grid.score(X_val, y_val)
            }
        except Exception as e:
            print(f"Error in Random Forest grid search: {str(e)}")
            grid_search_results['RandomForest'] = {'error': str(e)}

        # XGBoost parameters
        try:
            print("Performing grid search for XGBoost...")
            xgb_params = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5],
                'learning_rate': [0.01, 0.1],
                'subsample': [0.8, 1.0]
            }
            xgb = XGBRegressor(random_state=42)
            xgb_grid = GridSearchCV(xgb, xgb_params, cv=5, n_jobs=1, scoring='r2')  # Using n_jobs=1
            xgb_grid.fit(X_train, y_train)
            grid_search_results['XGBoost'] = {
                'best_params': xgb_grid.best_params_,
                'best_score': xgb_grid.best_score_,
                'validation_score': xgb_grid.score(X_val, y_val)
            }
        except Exception as e:
            print(f"Error in XGBoost grid search: {str(e)}")
            grid_search_results['XGBoost'] = {'error': str(e)}

        # Decision Tree parameters
        try:
            print("Performing grid search for Decision Tree...")
            dt_params = {
                'max_depth': [5, 10, None],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2],
                'max_features': ['auto', 'sqrt']
            }
            dt = DecisionTreeRegressor(random_state=42)
            dt_grid = GridSearchCV(dt, dt_params, cv=5, n_jobs=1, scoring='r2')  # Using n_jobs=1
            dt_grid.fit(X_train, y_train)
            grid_search_results['DecisionTree'] = {
                'best_params': dt_grid.best_params_,
                'best_score': dt_grid.best_score_,
                'validation_score': dt_grid.score(X_val, y_val)
            }
        except Exception as e:
            print(f"Error in Decision Tree grid search: {str(e)}")
            grid_search_results['DecisionTree'] = {'error': str(e)}

        # CatBoost parameters
        try:
            print("Performing grid search for CatBoost...")
            catboost_params = {
                'iterations': [100, 200],
                'learning_rate': [0.01, 0.1],
                'depth': [4, 6],
                'l2_leaf_reg': [3, 5]
            }
            catboost = CatBoostRegressor(verbose=False, random_state=42)
            catboost_grid = GridSearchCV(catboost, catboost_params, cv=5, n_jobs=1, scoring='r2')  # Using n_jobs=1
            catboost_grid.fit(X_train, y_train)
            grid_search_results['CatBoost'] = {
                'best_params': catboost_grid.best_params_,
                'best_score': catboost_grid.best_score_,
                'validation_score': catboost_grid.score(X_val, y_val)
            }
        except Exception as e:
            print(f"Error in CatBoost grid search: {str(e)}")
            grid_search_results['CatBoost'] = {'error': str(e)}

        return grid_search_results

    def handle_nan_values(self, df):
        """Replace NaN values with climatological means."""
        import pandas as pd
        import numpy as np

        # Create a copy of the dataframe
        df = pd.DataFrame(df)
        if df.shape[1] < 5:
            df.columns = ['year', 'month', 'day', 3]
        else:
            df.columns = ['year', 'month', 'day', 3, 4] + df.columns[5:].tolist()

        # Create month-day grouping for climatological means
        df['month_day'] = df['month'].astype(str).str.zfill(2) + '-' + df['day'].astype(str).str.zfill(2)

        # For each column that needs processing (columns 3 and 4)
        for col in [3, 4]:
            if col in df.columns:
                # Convert -999 to NaN
                df[col] = df[col].replace(-999.000, np.nan)

                # Calculate climatological means for each month-day combination
                climatological_means = df.groupby('month_day')[col].mean()

                # Replace NaN values with climatological means
                for idx in df[df[col].isna()].index:
                    month_day = df.loc[idx, 'month_day']
                    df.loc[idx, col] = climatological_means[month_day]

        # Drop the helper column
        df = df.drop('month_day', axis=1)

        return df.values

    def create_results_zip(self):
        """Create a zip file of all results"""


        # Create the results directory path

        results_dir = f"{settings.MEDIA_ROOT}/ml_results/{self.user_id}_{self.group_id}/"

        zip_filename = f"{results_dir}results_{self.user_id}_{self.group_id}_{self.sim_id}.zip"

        # Create a temporary directory to copy files
        temp_dir = f"{results_dir}temp_{self.user_id}_{self.group_id}"

        try:
            # First, create a temporary directory
            os.makedirs(temp_dir, exist_ok=True)

            # Wait a moment to ensure all files are fully written
            time.sleep(2)

            # Copy all files to temporary directory
            print("Copying files to temporary directory...")
            for root, dirs, files in os.walk(results_dir):
                for file in files:
                    # Skip if it's a zip file
                    if file.endswith('.zip'):
                        continue

                    src_path = os.path.join(root, file)
                    # Create relative path
                    rel_path = os.path.relpath(src_path, results_dir)
                    dst_path = os.path.join(temp_dir, rel_path)

                    # Create necessary directories
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    # Copy file
                    try:
                        shutil.copy2(src_path, dst_path)
                    except Exception as e:
                        print(f"Warning: Could not copy {file}: {str(e)}")

            # Create zip file from temporary directory
            print("Creating zip file...")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        try:
                            zipf.write(file_path, arcname)
                            print(f"added file {file}")
                        except Exception as e:
                            print(f"Warning: Could not add {file} to zip: {str(e)}")

            print(f"Results have been zipped successfully to: {zip_filename}")

        except Exception as e:
            print(f"Error creating zip file: {str(e)}")
            return None

        finally:
            # Clean up temporary directory
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Could not remove temporary directory: {str(e)}")

        return zip_filename

    def run(self):
        """Main execution method"""
        # Set data path based on model type
        if self.model == "air2water":
            usercalibrationdatapath = self.air2waterusercalibrationpath
            uservalidationdatapath = self.air2wateruservalidationpath
        elif self.model == "air2stream":  # air2stream
            usercalibrationdatapath = self.air2streamusercalibrationpath
            uservalidationdatapath = self.air2streamuservalidationpath

        # Load calibration data
        df_calibration = np.loadtxt(usercalibrationdatapath)

        # Handle NaN values before any other processing
        df_calibration = self.handle_nan_values(df_calibration)

        # Apply yearly data processing and interpolation if needed
        if self.interpolate:
            print("Interpolating...")
            processor = YearlyDataProcessor(df_calibration, self.n_data_interpolate)
            df_calibration, num_missing_col3, missing_col3 = processor.mean_year()

        # Process validation data based on validation_required option
        if not self.validation_required:
            # Use separate calibration and validation files
            calibration_data = df_calibration
            try:
                validation_data = np.loadtxt(uservalidationdatapath)
                validation_data = self.handle_nan_values(validation_data)
            except:
                print("Validation file not found for validation_required=False")
                return None
        elif self.validation_required == "Uniform Percentage":
            # Use sklearn's train_test_split for uniform percentage split
            calibration_data, validation_data = train_test_split(df_calibration,
                                                                 test_size=self.percent / 100,
                                                                 shuffle=True,
                                                                 random_state=42)
        elif self.validation_required == "Random Percentage":
            # Split calibration data randomly
            mask = np.random.rand(len(df_calibration)) < (self.percent / 100)
            calibration_data = df_calibration[~mask]
            validation_data = df_calibration[mask]
        elif self.validation_required == "Uniform Number":
            # Split calibration data uniformly by taking every nth sample
            indices = np.arange(len(df_calibration))
            validation_indices = indices[self.percent - 1::self.percent]
            calibration_indices = np.delete(indices, validation_indices)
            calibration_data = df_calibration[calibration_indices]
            validation_data = df_calibration[validation_indices]

        # Prepare data for machine learning
        is_air2stream = (self.model == "air2stream")

        # Create feature sets and target variables with dates
        train_data = self.prepare_ml_data(calibration_data, is_air2stream)
        val_data = self.prepare_ml_data(validation_data, is_air2stream)

        # Scale the features
        X_train_scaled = self.scaler.fit_transform(train_data['X'])
        X_val_scaled = self.scaler.transform(val_data['X'])

        # Apply PCA transformation
        X_train_pca = self.pca.fit_transform(X_train_scaled)
        X_val_pca = self.pca.transform(X_val_scaled)

        # Add Kernel PCA transformation
        X_train_kpca = self.kpca.fit_transform(X_train_scaled)
        X_val_kpca = self.kpca.transform(X_val_scaled)

        # Add LDA transformation
        # Discretize targets for LDA
        y_train_discrete, y_val_discrete = self.discretize_target(train_data['y'], val_data['y'])

        # Apply LDA transformation using discretized targets
        X_train_lda = self.lda.fit_transform(X_train_scaled, y_train_discrete)
        X_val_lda = self.lda.transform(X_val_scaled)

        # Calculate explained variance ratio for PCA
        explained_variance_ratio = self.pca.explained_variance_ratio_
        print(f"PCA explained variance ratio: {explained_variance_ratio}")

        # Train SVR and MLR on original scaled data
        svr_results_orig = self.train_svr(
            X_train_scaled, train_data['y'],
            X_val_scaled, val_data['y']
        )
        mlr_results_orig = self.train_mlr(
            X_train_scaled, train_data['y'],
            X_val_scaled, val_data['y']
        )

        # Train all models on original scaled data
        models_orig = {
            'svr': self.train_svr(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'mlr': self.train_mlr(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'xgboost': self.train_xgboost(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'random_forest': self.train_random_forest(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'decision_tree': self.train_decision_tree(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'catboost': self.train_catboost(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'polynomial': self.train_polynomial(X_train_scaled, train_data['y'], X_val_scaled, val_data['y']),
            'ann': self.train_ann(X_train_scaled, train_data['y'], X_val_scaled, val_data['y'])
        }

        # Train all models on PCA transformed data
        models_pca = {
            'svr': self.train_svr(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'mlr': self.train_mlr(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'xgboost': self.train_xgboost(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'random_forest': self.train_random_forest(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'decision_tree': self.train_decision_tree(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'catboost': self.train_catboost(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'polynomial': self.train_polynomial(X_train_pca, train_data['y'], X_val_pca, val_data['y']),
            'ann': self.train_ann(X_train_pca, train_data['y'], X_val_pca, val_data['y'])
        }

        models_kpca = {
            'svr': self.train_svr(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'mlr': self.train_mlr(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'xgboost': self.train_xgboost(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'random_forest': self.train_random_forest(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'decision_tree': self.train_decision_tree(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'catboost': self.train_catboost(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'polynomial': self.train_polynomial(X_train_kpca, train_data['y'], X_val_kpca, val_data['y']),
            'ann': self.train_ann(X_train_kpca, train_data['y'], X_val_kpca, val_data['y'])
        }

        # Add training with LDA transformed data
        models_lda = {
            'svr': self.train_svr(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'mlr': self.train_mlr(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'xgboost': self.train_xgboost(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'random_forest': self.train_random_forest(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'decision_tree': self.train_decision_tree(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'catboost': self.train_catboost(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'polynomial': self.train_polynomial(X_train_lda, train_data['y'], X_val_lda, val_data['y']),
            'ann': self.train_ann(X_train_lda, train_data['y'], X_val_lda, val_data['y'])
        }

        # Save results for all models with original data
        results_orig = {}
        for model_name, model_results in models_orig.items():
            train_df = self.save_results_csv(
                model_results['train_pred'],
                train_data,
                f'calibration_{model_name}',
                self.owd
            )
            val_df = self.save_results_csv(
                model_results['val_pred'],
                val_data,
                f'validation_{model_name}',
                self.owd
            )

            # Create plots for each model
            self.plot_results(
                train_df,
                f'calibration_{model_name}',
                self.owd,
                "calib",
                model_results['cv_mean'],
                model_results['cv_std']
            )
            self.plot_results(
                val_df,
                f'validation_{model_name}',
                self.owd,
                "valid"
            )

            results_orig[model_name] = {
                'train': train_df,
                'val': val_df,
                'cv_scores': model_results['cv_scores'],
                'cv_mean': model_results['cv_mean'],
                'cv_std': model_results['cv_std']
            }

        # Save results for all models with PCA transformed data
        results_pca = {}
        for model_name, model_results in models_pca.items():
            train_df = self.save_results_csv(
                model_results['train_pred'],
                train_data,
                f'calibration_{model_name}_pca',
                self.owd
            )
            val_df = self.save_results_csv(
                model_results['val_pred'],
                val_data,
                f'validation_{model_name}_pca',
                self.owd
            )

            # Create plots for each model with PCA
            self.plot_results(
                train_df,
                f'calibration_{model_name}_pca',
                self.owd,
                "calib",
                model_results['cv_mean'],
                model_results['cv_std']
            )
            self.plot_results(
                val_df,
                f'validation_{model_name}_pca',
                self.owd,
                "valid"
            )

            results_pca[model_name] = {
                'train': train_df,
                'val': val_df,
                'cv_scores': model_results['cv_scores'],
                'cv_mean': model_results['cv_mean'],
                'cv_std': model_results['cv_std']
            }

        results_kpca = {}
        for model_name, model_results in models_kpca.items():
            train_df = self.save_results_csv(
                model_results['train_pred'],
                train_data,
                f'calibration_{model_name}_kpca',
                self.owd
            )
            val_df = self.save_results_csv(
                model_results['val_pred'],
                val_data,
                f'validation_{model_name}_kpca',
                self.owd
            )

            self.plot_results(
                train_df,
                f'calibration_{model_name}_kpca',
                self.owd,
                "calib",
                model_results['cv_mean'],
                model_results['cv_std']
            )
            self.plot_results(
                val_df,
                f'validation_{model_name}_kpca',
                self.owd,
                "valid"
            )

            results_kpca[model_name] = {
                'train': train_df,
                'val': val_df,
                'cv_scores': model_results['cv_scores'],
                'cv_mean': model_results['cv_mean'],
                'cv_std': model_results['cv_std']
            }

        # Save results for LDA
        results_lda = {}
        for model_name, model_results in models_lda.items():
            train_df = self.save_results_csv(
                model_results['train_pred'],
                train_data,
                f'calibration_{model_name}_lda',
                self.owd
            )
            val_df = self.save_results_csv(
                model_results['val_pred'],
                val_data,
                f'validation_{model_name}_lda',
                self.owd
            )

            self.plot_results(
                train_df,
                f'calibration_{model_name}_lda',
                self.owd,
                "calib",
                model_results['cv_mean'],
                model_results['cv_std']
            )
            self.plot_results(
                val_df,
                f'validation_{model_name}_lda',
                self.owd,
                "valid"
            )

            results_lda[model_name] = {
                'train': train_df,
                'val': val_df,
                'cv_scores': model_results['cv_scores'],
                'cv_mean': model_results['cv_mean'],
                'cv_std': model_results['cv_std']
            }

        # Perform grid search on original data
        print("\nPerforming grid search on original scaled data...")
        grid_search_results_orig = self.perform_grid_search(X_train_scaled, train_data['y'],
                                                            X_val_scaled, val_data['y'])

        # Perform grid search on PCA transformed data
        print("\nPerforming grid search on PCA transformed data...")
        grid_search_results_pca = self.perform_grid_search(X_train_pca, train_data['y'],
                                                           X_val_pca, val_data['y'])

        # Perform grid search on Kernel PCA transformed data
        print("\nPerforming grid search on Kernel PCA transformed data...")
        grid_search_results_kpca = self.perform_grid_search(X_train_kpca, train_data['y'],
                                                            X_val_kpca, val_data['y'])

        # Perform grid search on LDA transformed data
        print("\nPerforming grid search on LDA transformed data...")
        grid_search_results_lda = self.perform_grid_search(X_train_lda, train_data['y'],
                                                           X_val_lda, val_data['y'])

        # Print grid search results
        print("\n" + "=" * 50)
        print("GRID SEARCH RESULTS")
        print("=" * 50)

        for data_type, results in [("Original", grid_search_results_orig),
                                   ("PCA", grid_search_results_pca),
                                   ("Kernel PCA", grid_search_results_kpca),
                                   ("LDA", grid_search_results_lda)]:
            print(f"\n{data_type} Data Results:")
            print("-" * 40)
            for model, result in results.items():
                print(f"\n{model}:")
                print(f"Best Parameters: {result['best_params']}")
                print(f"Best CV Score: {result['best_score']:.3f}")
                print(f"Validation Score: {result['validation_score']:.3f}")

        # Create zip file of results
        print("\nCreating zip file of all results...")
        zip_file_path = self.create_results_zip()

        # Return results including zip file path
        return {
            'original': results_orig,
            'pca': results_pca,
            'kpca': results_kpca,
            'lda': results_lda,
            'explained_variance_ratio': explained_variance_ratio,
            'grid_search': {
                'original': grid_search_results_orig,
                'pca': grid_search_results_pca,
                'kpca': grid_search_results_kpca,
                'lda': grid_search_results_lda
            },
            'zip_file': zip_file_path
        }

if __name__ == "__main__":
    start_time = time.time()

    # Test paths - replace with your actual file paths
    calibration_file = '/home/riddick/Downloads/SIO_2011_cc.txt'
    validation_file = '/home/riddick/Downloads/SIO_2011_cv.txt'

    # Initialize ML Model
    ml_model = ML_Model(
        user_id=1,
        group_id=1,
        model="air2stream",
        interpolate=True,
        n_data_interpolate=7,
        validation_required="Uniform Percentage",
        percent=20,
        air2streamusercalibrationpath=calibration_file,
        air2streamuservalidationpath=validation_file
    )

    # Run the models and get results
    results = ml_model.run()

    if results is not None:
        print("\n" + "="*50)
        print("Results Summary")
        print("="*50)

        # Function to print model results
        def print_model_results(model_name, model_data, data_type="Original"):
            print(f"\n{data_type} Data - {model_name} Results:")
            print("-" * 40)
            print(f"Training R² Score: {model_data['cv_mean']:.3f} ± {model_data['cv_std']:.3f}")
            val_r2 = r2_score(
                model_data['val']['Evaluation_(Water_temperature_data)'],
                model_data['val']['Best_simulation']
            )
            print(f"Validation R² Score: {val_r2:.3f}")

        # Print results for original data
        print("\nORIGINAL DATA RESULTS:")
        print("="*50)
        for model_name, model_results in results['original'].items():
            print_model_results(model_name.upper(), model_results)

        # Print results for PCA data
        print("\nPCA TRANSFORMED DATA RESULTS:")
        print("="*50)
        print(f"\nExplained Variance Ratio: {results['explained_variance_ratio']}")
        for model_name, model_results in results['pca'].items():
            print_model_results(model_name.upper(), model_results, "PCA")

        # Print results for Kernel PCA data
        print("\nKERNEL PCA TRANSFORMED DATA RESULTS:")
        print("=" * 50)
        for model_name, model_results in results['kpca'].items():
            print_model_results(model_name.upper(), model_results, "Kernel PCA")

        # Print results for LDA data
        print("\nLDA TRANSFORMED DATA RESULTS:")
        print("=" * 50)
        for model_name, model_results in results['lda'].items():
            print_model_results(model_name.upper(), model_results, "LDA")

        # Find best performing model
        best_val_r2 = -float('inf')
        best_model = None
        best_type = None

        for data_type in ['original', 'pca']:
            for model_name, model_results in results[data_type].items():
                val_r2 = r2_score(
                    model_results['val']['Evaluation_(Water_temperature_data)'],
                    model_results['val']['Best_simulation']
                )
                if val_r2 > best_val_r2:
                    best_val_r2 = val_r2
                    best_model = model_name
                    best_type = data_type

        print("\n" + "="*50)
        print("BEST MODEL SUMMARY")
        print("="*50)
        print(f"Best Performing Model: {best_model.upper()} ({'Original' if best_type == 'original' else 'PCA'} data)")
        print(f"Best Validation R² Score: {best_val_r2:.3f}")
        print(f"Training R² Score: {results[best_type][best_model]['cv_mean']:.3f} ± {results[best_type][best_model]['cv_std']:.3f}")

        # Print execution time
        total_time = time.time() - start_time
        print(f"\nTotal execution time: {total_time:.2f} seconds")

        # Print file locations
        print("\n" + "="*50)
        print("OUTPUT FILES LOCATION")
        print("="*50)
        results_dir = f"{ml_model.owd}/results/{ml_model.user_id}_{ml_model.group_id}/"
        print(f"All results and plots have been saved to: {results_dir}")
        print("\nFiles generated:")
        print("- CSV files: results_[model]_[calibration/validation].csv")
        print("- Plot files: [calibration/validation]_best_modelrun_[model].png")
    else:
        print("Error: No results were generated. Please check your input files and parameters.")