# -*- coding: utf-8 -*-
"""Diabetes Classification With LightGBM(%89 Acc).ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1NMmgiCTr3Q4jajW5BrtMSDBQrvcpDBiF
"""

#Libraries

!pip install dask
import joblib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sbn
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier, AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_validate, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score,roc_curve
import warnings
warnings.filterwarnings('ignore')

#read file
df = pd.read_csv('/content/drive/MyDrive/content/diabetes.csv')

#EDA(Exploratory Data Analysis)
def eda(dataframe):
    print(f"""

    -- dtypes --

    {dataframe.dtypes}

    -- NaN Values --

    {dataframe.isnull().sum()}

    -- Shape --

    {dataframe.shape}

    -- Unique --

    {df.apply(lambda x: x.nunique())}

    -- Head --
    """)


    return dataframe.head()
eda(df)

#Tail
df.describe().T

sbn.clustermap(df.corr(), annot = True, fmt = ".2f")

#Data Pre-Processing
def grab_col_names(dataframe, cat_th=10, car_th=20):
    # cat_cols, cat_but_car
    cat_cols = [col for col in dataframe.columns if dataframe[col].dtypes == "O"]
    num_but_cat = [col for col in dataframe.columns if dataframe[col].nunique() < cat_th and
                   dataframe[col].dtypes != "O"]
    cat_but_car = [col for col in dataframe.columns if dataframe[col].nunique() > car_th and
                   dataframe[col].dtypes == "O"]
    cat_cols = cat_cols + num_but_cat
    cat_cols = [col for col in cat_cols if col not in cat_but_car]

    # num_cols
    num_cols = [col for col in dataframe.columns if dataframe[col].dtypes != "O"]
    num_cols = [col for col in num_cols if col not in num_but_cat]

    print(f"Observations: {dataframe.shape[0]}")
    print(f"Variables: {dataframe.shape[1]}")
    print(f'cat_cols: {len(cat_cols)}')
    print(f'num_cols: {len(num_cols)}')
    print(f'cat_but_car: {len(cat_but_car)}')
    print(f'num_but_cat: {len(num_but_cat)}')
    return cat_cols, num_cols, cat_but_car

cat_cols, num_cols, cat_but_car = grab_col_names(df)

cat_cols, num_cols, cat_but_car

plt.figure(figsize = (16,8))
for i,x in enumerate(num_cols):
  plt.subplot(2,4,i+1)
  sbn.histplot(df[x])

plt.figure(figsize = (16,8))
for i,x in enumerate(num_cols):
  plt.subplot(2,4,i+1)
  sbn.boxplot(df[x])

#Outlier Analysis¶
def outlier_thresholds(dataframe, col_name, q1=0.25, q3=0.75):
    quartile1 = dataframe[col_name].quantile(q1)
    quartile3 = dataframe[col_name].quantile(q3)
    interquantile_range = quartile3 - quartile1
    up_limit = quartile3 + 1.5 * interquantile_range
    low_limit = quartile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def check_outlier(dataframe, col_name):
    low_limit, up_limit = outlier_thresholds(dataframe, col_name)
    if dataframe[(dataframe[col_name] > up_limit) | (dataframe[col_name] < low_limit)].any(axis=None):
        return True
    else:
        return False

def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = outlier_thresholds(dataframe, variable)
    dataframe.loc[(dataframe[variable] < low_limit), variable] = low_limit
    dataframe.loc[(dataframe[variable] > up_limit), variable] = up_limit

for x in num_cols:
  print(x,check_outlier(df,x))

for x in num_cols:
  replace_with_thresholds(df,x)

plt.figure(figsize = (16,8))
for i,x in enumerate(num_cols):
  plt.subplot(2,4,i+1)
  sbn.histplot(df[x])

plt.figure(figsize = (16,8))
for i,x in enumerate(num_cols):
  plt.subplot(2,4,i+1)
  sbn.boxplot(df[x])

plt.pie(df['Outcome'].value_counts(),
                   explode      = [0.0, 0.25],
                   startangle   = 30,
                   shadow       = True,
                   colors       = ['#004d99', '#ac7339'],
                   textprops    = {'fontsize': 8, 'fontweight': 'bold', 'color': 'white'},
                   pctdistance  = 0.50, autopct = '%1.2f%%'
                  );

df.describe()[['Insulin','SkinThickness']].loc['min',:]

# look at the number and ratio of these values

zero_count = pd.DataFrame(df[['Insulin','SkinThickness']].apply(lambda x: x.value_counts()).loc[0,:])
zero_ratio = zero_count /df[['Insulin','SkinThickness']].shape[0]

pd.concat([zero_count,zero_ratio], axis = 1)

df['Insulin'] = df['Insulin'].where((df['Insulin'] > 0)).fillna(df.groupby('Outcome')["Insulin"].transform("mean"))
df['SkinThickness'] = df['SkinThickness'].where((df['SkinThickness'] > 0)).fillna(df.groupby('Outcome')["SkinThickness"].transform("mean"))

df.describe()[['Insulin','SkinThickness']].loc['min',:]

#Feature Engineering
plt.subplot(1,2,1)
sbn.histplot(df['Glucose'])
plt.subplot(1,2,2)
sbn.histplot(df['Age'])

df.loc[(df['Glucose'] < 150) & (df['Glucose'] > 50) & (df["Age"] <= 45), "Gul_Age_Cat"] = "normal_young"
df.loc[(df['Glucose'] < 150) & (df['Glucose'] > 50) & (df["Age"] > 45), "Gul_Age_Cat"] = "normal_old"
df.loc[((df['Glucose'] > 150) | (df['Glucose'] < 50)) & (df["Age"] <= 45), "Gul_Age_Cat"] = "not_normal_young"
df.loc[((df['Glucose'] > 150) | (df['Glucose'] < 50)) & (df["Age"] > 45), "Gul_Age_Cat"] = "not_normal_old"

#categorized the insulin values

df.loc[(df['Insulin'] < 30), "Insulin_level"] = "Low"
df.loc[(df['Insulin'] >= 30) & (df['Insulin'] <= 120), "Insulin_level"] = "Normal"
df.loc[(df['Insulin'] >120), "Insulin_level"] = "High"

#categorizing values
df.loc[(df['Glucose'] < 50), "Glucose_level"] = "Low"
df.loc[(df['Glucose'] >= 50) & (df['Glucose'] <= 140), "Insulin_level"] = "Normal"
df.loc[(df['Glucose'] >140), "Glucose_level"] = "High"

#Risk and Non-Risk
df.loc[((df['Insulin'] >= 50) & (df['Insulin'] <= 140)) &
       ((df['BMI'] >= 25) & (df['BMI'] <= 36)) &
       ((df['Glucose'] >= 50) & (df['Glucose'] <= 150)) &
       ((df['SkinThickness'] >= 20) & (df['SkinThickness'] <= 32))
       , "Life_level"] = "Not_Risk"
df['Life_level'].fillna('At_Risk',inplace = True)

sbn.histplot(df['BMI'])

#categorized the BMI Variable in the ranges I specified

df['NEW_BMI_RANGE'] = pd.cut(x=df['BMI'], bins=[-1, 18.5, 24.9, 29.9, 100],
                                        labels=["underweight", "healty", "overweight", "obese"])

sbn.histplot(df['BloodPressure'])

#categorized the BloodPressure Variable in the ranges I specified

df['NEW_BLOODPRESSURE'] = pd.cut(x=df['BloodPressure'], bins=[-1, 79, 89, 123],
                                            labels=["normal", "hs1", "hs2"])

df[cat_cols] = df[cat_cols].astype('category')

df_dummy = pd.get_dummies(df,drop_first = True)
df_dummy.head()

#Scaling
X_scaled = StandardScaler().fit_transform(df_dummy[num_cols])
df_dummy[num_cols] = pd.DataFrame(X_scaled, columns=df_dummy[num_cols].columns)

y = df["Outcome"]
x = df_dummy.drop('Outcome_1',axis = 1)

#Create Models
def base_models(X, y, scoring="accuracy"):
    print("Base Models....")
    classifiers = [('LR', LogisticRegression()),
                   ('KNN', KNeighborsClassifier()),
                   ("SVC", SVC()),
                   ("CART", DecisionTreeClassifier()),
                   ("RF", RandomForestClassifier()),
                   ('Adaboost', AdaBoostClassifier()),
                   ('GBM', GradientBoostingClassifier()),
                   ('XGBoost', XGBClassifier(use_label_encoder=False, eval_metric='logloss')),
                   ('LightGBM', LGBMClassifier()),
                   # ('CatBoost', CatBoostClassifier(verbose=False))
                   ]

    for name, classifier in classifiers:
        cv_results = cross_validate(classifier, X, y, cv=5, scoring=scoring)
        print(f"{scoring}: {round(cv_results['test_score'].mean(), 4)} ({name}) ")

knn_params = {"n_neighbors": range(2, 50)}

cart_params = {'max_depth': range(1, 20),
               "min_samples_split": range(2, 30)}

rf_params = {"max_depth": [8, 15, None],
             "max_features": [5, 7, "auto"],
             "min_samples_split": [15, 20],
             "n_estimators": [200, 300]}

xgboost_params = {"learning_rate": [0.1, 0.01],
                  "max_depth": [5, 8],
                  "n_estimators": [100, 200],
                  "colsample_bytree": [0.5, 1]}

lightgbm_params = {"learning_rate": [0.01, 0.1],
                   "n_estimators": [300, 500],
                   "colsample_bytree": [0.7, 1]}

classifiers = [('KNN', KNeighborsClassifier(), knn_params),
               ("CART", DecisionTreeClassifier(), cart_params),
               ("RF", RandomForestClassifier(), rf_params),
               ('XGBoost', XGBClassifier(use_label_encoder=False, eval_metric='logloss'), xgboost_params),
               ('LightGBM', LGBMClassifier(), lightgbm_params)]

def hyperparameter_optimization(X, y, cv=5, scoring="accuracy"):
    print("Hyperparameter Optimization....")
    best_models = {}
    for name, classifier, params in classifiers:
        print(f"########## {name} ##########")
        cv_results = cross_validate(classifier, X, y, cv=cv, scoring=scoring)
        print(f"{scoring} (Before): {round(cv_results['test_score'].mean(), 4)}")

        gs_best = GridSearchCV(classifier, params, cv=cv, n_jobs=-1, verbose=False).fit(X, y)
        final_model = classifier.set_params(**gs_best.best_params_)

        cv_results = cross_validate(final_model, X, y, cv=cv, scoring=scoring)
        print(f"{scoring} (After): {round(cv_results['test_score'].mean(), 4)}")
        print(f"{name} best params: {gs_best.best_params_}", end="\n\n")
        best_models[name] = final_model
    return best_models

def voting_classifier(best_models, X, y):
    print("Voting Classifier...")
    voting_clf = VotingClassifier(estimators=[('KNN', best_models["KNN"]), ('RF', best_models["RF"]),
                                              ('LightGBM', best_models["LightGBM"])],
                                  voting='soft').fit(X, y)
    cv_results = cross_validate(voting_clf, X, y, cv=3, scoring=["accuracy", "f1", "roc_auc"])
    print(f"Accuracy: {cv_results['test_accuracy'].mean()}")
    print(f"F1Score: {cv_results['test_f1'].mean()}")
    print(f"ROC_AUC: {cv_results['test_roc_auc'].mean()}")
    return voting_clf

def fit(x,y):
    base_models(x, y)
    best_models = hyperparameter_optimization(x, y)
    voting_clf = voting_classifier(best_models, x, y)
    joblib.dump(voting_clf, "voting_clf.pkl")
    return voting_clf,best_models

voting_clf,best_models = fit(x,y)