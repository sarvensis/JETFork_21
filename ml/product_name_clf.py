import fasttext
import joblib
import pandas as pd
import compress_fasttext

from lightgbm import LGBMClassifier
from multipledispatch import dispatch

import fasttext
from lightgbm import LGBMClassifier
import joblib
import pandas as pd
from multipledispatch import dispatch
import razdel
import re

russian_stopwords = open('stopwords-ru.txt', 'r').read().split('\n')

def tokenize_with_razdel(text):
    tokens = [token.text for token in razdel.tokenize(text)]
    
    return tokens

class ProductNameClassifier:
    def __init__(self):
        self.ft_model = fasttext.load_model('fb_model.bin')
        self.model_level_1 = joblib.load('level_1.pkl')
        self.vectorizer = joblib.load('vectorizer_level_2.pkl')
        self.model_level_2 = joblib.load('model_level_2.pkl')
        self.all_categories = pd.read_csv('all_categories.csv', sep=';')
    
    @dispatch(str)
    def predict(self, text:str) -> (int, float):
        """
        Функция для обработки текста 
        """
        text = text.replace('\n', ' ')
        text = ' '.join(self.delete_stopwords(self.delete_punctuation((text))))
        text_vector = self.ft_model.get_sentence_vector(text).reshape(1, -1)
        label = int(self.model_level_1.predict(text_vector)[0])
        probability = self.model_level_1.predict_proba(text_vector)
        return label, probability.max()  
    
    @dispatch(str)
    def predict_level_2(self, text:str) -> (int, float):
        """
        Функция для обработки текста 
        """
        text = text.replace('\n', ' ')
        text = ' '.join(self.delete_stopwords(self.delete_punctuation((text))))
        text_vector = self.vectorizer.transform([text])
        label = self.model_level_2.predict(text_vector)[0]
        probability = self.model_level_2.predict_proba(text_vector)
        return label, probability.max() 
    
    @dispatch(str, int)
    def predict(self, text:str, user_label:int) -> (str, float, int):
        """
        Функция для обработки текста и метки 
        """
        text = text.replace('\n', ' ')
        text = ' '.join(self.delete_stopwords(self.delete_punctuation((text))))
        text_vector = self.ft_model.get_sentence_vector(text).reshape(1, -1)
        label = self.model_level_1.predict(text_vector)[0]
        probability = self.model_level_1.predict_proba(text_vector)
        is_equal = label == user_label
        return label, probability.max(), is_equal
    
    
    def get_category_sim(self, product_name:str, category: str):
        all_categories['sim'] = self.get_similarity(product_name, self.all_categories)
        all_categories = all_categories.sort_values(by=['sim', 'count'], ascending=False)
        label, probability = all_categories[['level_2', 'sim']].values[0]
        return label, probability, category==label

    def get_similarity(self, product_name:str):
        probability = []
        for category in self.all_categories:
            probability.append(fuzz.token_sort_ratio(short_rp_name, category)/100)
        return probability
    
    def tokenize_with_razdel(self, text):
        tokens = [token.text for token in razdel.tokenize(text)]

        return tokens
    
    def delete_stopwords(self, s):
        return ' '.join([word for word in (re.sub(r'[()\s+]', u' ', s)).split() if word.lower() not in russian_stopwords]).split()

    
    def delete_punctuation(self, s):
        return re.sub(r'[®?"\'-_/.:?!1234567890()%<>;,+#$&№\s+]', u' ', s)
    
    def get_okpd(self, line) -> int :
        okpd_re = re.compile('окпд2\x20*(\d{2}\.\d{2}\.\d{2}\.\d{3})')
        res = re.findall(okpd_re, line.lower())
        return res[0] if len(res) > 0 else None 
        
        

if __name__ == '__main__':
    #Пример использования
    df = pd.DataFrame.from_dict(
    {'product_name': {0: 'Парацетамол таблетки 500 мг 10 шт., упаковки ячейковые контурные (2), пачки картонные, рег № ЛС-001364 от 06.08.2010, серия 190618, партия 59110 упаковок, годен до 01.07.2022, производства  ОАО "Фармстандарт-Лексредства", ИНН 4631002737, 305022, Курская область, Курск, ул. 2-я Агрегатная, 1А/18, Россия, код ОКПД2 21.20.10.232 ',
      1: 'Перезаряжаемая литий-ионная батарея торговой марки HUAWEI модель HB642735ECW',
      2: 'Перезаряжаемая литий-ионная батарея торговой марки vivo модель B-E8',
      3: 'Аппарат вакуумно-лазерной терапии стоматологический АВЛТ-"ДЕСНА" (по методу Кулаженко-Лепилина)',
      4: 'Блоки оконные и балконные дверные из алюминиевых профилей системы "INICIAL" серии "IW63" фирмы ООО "Урало-Сибирская профильная компания"'},
     'category_1': {0: 9300, 1: 3482, 2: 3482, 3: 9444, 4: 5270}
    })

    product_name_clf = ProductNameClassifier()

    #если есть и метка от пользователя и текст
    label, probability, is_equal = product_name_clf.predict(df['product_name'][0], 9300)
    print('1:   ', label, probability, is_equal )

    #если только текст
    label, probability = product_name_clf.predict(df['product_name'][0])
    print('2:   ', label, probability)

    #Скоринг всего файла без метки от пользователя
    df[['model_label', 'probability']] = None
    df[['model_label', 'probability']] = df[['product_name']].apply(lambda x: product_name_clf.predict(*x),
                                                                                                        axis=1,
                                                                                                        result_type="expand")
    print('3:\n', df.head())
    #Скоринг всего файла с наличием метки от пользователя
    df[['model_label', 'probability', 'is_equal']] = None
    df[['model_label', 'probability', 'is_equal']] = df[['product_name', 'category_1']].apply(lambda x: product_name_clf.predict(*x),
                                                                                                        axis=1,
                                                                                                        result_type="expand")
    print('4:\n',df.head())
    
main()