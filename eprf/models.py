from django.db import models
from django.contrib.postgres.fields import ArrayField

from eprf.modules.nameClassifier import ProductNameClassifier

product_name_clf = ProductNameClassifier()

PRODUCT_STATUSES = [
    ('in processing', 'В обработке'),
    ('accepted', 'Принято'),
    ('analysis', 'Анализ'),
    ('rejected', 'Отказано'),
]

class Category(models.Model):
    # code = models.IntegerField("Код категории")
    code = models.IntegerField("Код категории")
    sub_code = models.TextField("Код подкатегории", null=True, blank=True)
    text = models.TextField("Наименование категория продукции")

    removed = models.BooleanField(default=False)


class Upload(models.Model):
    email = models.EmailField()
    ipaddress = models.GenericIPAddressField()
    datetime = models.DateTimeField(auto_now_add=True)


class Product(models.Model):
    name = models.TextField("Общее наименование продукции")
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE)

    category_model_label = models.ForeignKey(Category, on_delete=models.CASCADE)
    category_probability = models.FloatField(null=True, blank=True)
    category_is_equal = models.BooleanField(null=True, blank=True, default=None)
    category_light = models.IntegerField(null=True, blank=True, default=None)

    # model_label - Вариант, который предложила модель
    # probability - уверенность
    # is_equal - модель думает, что он совпал
    # light - светофор

    status = models.CharField(choices=PRODUCT_STATUSES, max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# --- Чистка словарей ---
# df1 = pd.read_csv('dictionary_level_2 (2).csv', sep=';')
# df1['category'] = df1['category'].str.strip()
# df1.drop_duplicates(subset=['level_2'], inplace=True)
# df2 = pd.read_excel('epp.xlsx', names=['level_1','category'])
# df2['category'] = df2['category'].str.strip()
# d1 = pd.concat([df1, df2], ignore_index=True).drop_duplicates(subset=['category'])
# d1.loc[d1['level_2'].isna(), 'level_2'] = d1.loc[d1['level_2'].isna(), 'level_1'].apply(lambda x: f'{x}.0')
# d1.to_csv('epp3.csv', encoding='utf-8-sig', index=False, sep=';')
