import os.path

import fasttext
# import fasttext_wheel
import joblib
import os
import pandas as pd

from lightgbm import LGBMClassifier
from multipledispatch import dispatch


class ProductNameClassifier:
    def __init__(self):
        self.model = joblib.load(os.path.join(os.getcwd(), 'eprf', 'modules', 'model.pkl'))
        self.ft_model = fasttext.load_model(os.path.join(os.getcwd(), 'eprf', 'modules', 'fb_model.bin'))

    @dispatch(str)
    def predict(self, text: str) -> (int, float):
        """
        Функция для обработки текста
        """
        text = text.replace('\n', ' ')
        text_vector = self.ft_model.get_sentence_vector(text).reshape(1, -1)
        label = int(self.model.predict(text_vector)[0])
        probability = self.model.predict_proba(text_vector)
        return label, probability.max()

    @dispatch(str, int)
    def predict(self, text: str, user_label: int) -> (str, float, int):
        """
        Функция для обработки текста и метки
        """
        text = text.replace('\n', ' ')
        text_vector = self.ft_model.get_sentence_vector(text).reshape(1, -1)
        label = int(self.model.predict(text_vector)[0])
        probability = self.model.predict_proba(text_vector)
        is_equal = label == user_label
        return label, probability.max(), is_equal