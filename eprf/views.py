from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
import pandas as pd
import json
import time
from io import BytesIO
from pathlib import Path

from eprf.models import Upload, Product, Category, product_name_clf


def main_page(request, *args, **kwargs):
    if request.method == 'GET':
        category_filters = Category.objects.distinct('code', 'text').filter(removed=False, sub_code__contains='.0')
        # subcategory_filters = Category.objects.distinct('sub_code', 'sub_text').filter(removed=False)
        return render(request, 'index.html', {'category_filters': category_filters})
    else:
        upload = Upload.objects.create(ipaddress=request.META.get('REMOTE_ADDR'), email='test@test.ts')
        upload.save()

        start_time = time.time()
        try:
            df = df_check(request.FILES['excelFile'])
        except Exception as e:
            return render(request, 'index.html', {'status': 'error', 'message': str(e)})

        if request.POST.get('report') == 'xlsx':
            with BytesIO() as b:
                with pd.ExcelWriter(b) as writer:
                    df.to_excel(writer, sheet_name=timezone.now().strftime('result_%Y_%m_%d'), index=False)
                filename = timezone.now().strftime('result_%Y_%m_%d.xlsx')
                res = HttpResponse(
                    b.getvalue(),  # Gives the Byte string of the Byte Buffer object
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                res['Content-Disposition'] = f'attachment; filename={filename}'
                return res
        else:
            return render(request, 'report.html',
                          {'now': timezone.now().strftime('%d %B %Y %H:%M:%S'), 'filename': request.FILES['excelFile'].name,
                           'count': len(df), 'time': time.time() - start_time,
                           **df.sort_values(by=['light', 'probability'], ascending=False).to_dict(orient='split')})


def report_json(request, *args, **kwargs):
    """ Множественная проверка, API"""
    upload = Upload.objects.create(ipaddress=request.META.get('REMOTE_ADDR'), email='test@test.ts')
    upload.save()
    start_time = time.time()
    try:
        df = df_check(request.FILES['excelFile'])
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'ok', 'result': df.to_json(), 'now': timezone.now().strftime('%d %B %Y %H:%M:%S'),
                         'filename': request.FILES['excelFile'].name,
                         'count': len(df), 'time': time.time() - start_time,
                         'message': "Файл успешно загружен. По результатам проверки Вам будет направлено письмо"})


def report_xlsx(request, *args, **kwargs):
    upload = Upload.objects.create(ipaddress=request.META.get('REMOTE_ADDR'), email='test@test.ts')
    upload.save()
    start_time = time.time()
    try:
        df = df_check(request.FILES['excelFile'])
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

    # with BytesIO() as b:
    #     writer = pd.ExcelWriter(b, engine='xlsxwriter')
    #     df.to_excel(writer, sheet_name='Sheet1')
    #     writer.save()

    with BytesIO() as b:
        with pd.ExcelWriter(b) as writer:
            df.to_excel(writer, sheet_name=timezone.now().strftime('result_%Y_%m_%d'), index=False)
        filename = timezone.now().strftime('result_%Y_%m_%d.xlsx')
        res = HttpResponse(
            b.getvalue(),  # Gives the Byte string of the Byte Buffer object
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        res['Content-Disposition'] = f'attachment; filename={filename}'
        return res


def df_check(file) -> pd.DataFrame:
    """ Прогон датафрейма через модель
    на вход подается бинарный файл
    """
    original_df = None
    file_format = Path(file.name).suffix
    if file_format == '.xlsx':
        original_df = pd.read_excel(file, dtype=str)
    elif file_format == '.csv':
        original_df = pd.read_csv(file, sep=';', dtype=str)
    else:
        raise Exception('Неправильный формат файла. Разрешенные форматы: .csv, .xslx')

    df = pd.DataFrame()
    try:
        df['product_name'] = original_df['Общее наименование продукции'].astype(str)
        df['category_1'] = original_df['Раздел ЕП РФ (Код из ФГИС ФСА для подкатегории продукции)'].astype(str)
    except:
        raise Exception('Файл содержит неправильный формат, пожалуйста, скачайте шаблон для заполнения данных')

    # product_name_clf = ProductNameClassifier()
    # Избавляемся от `;`
    df = df[~df['category_1'].str.contains(r'[;\.]')]

    df['category_1'] = df['category_1'].astype(int)
    df[['model_label', 'probability', 'is_equal', 'light']] = None
    df_with_cat1 = df[~df['category_1'].isnull()]
    df_without_cat1 = df[df['category_1'].isnull()]

    if len(df_without_cat1) > 0:
        # Скоринг всего файла без метки от пользователя
        df_without_cat1[['model_label', 'probability']] = df_without_cat1[['product_name']].apply(
            lambda x: product_name_clf.predict(*x),
            axis=1,
            result_type="expand")
    if len(df_with_cat1) > 0:
        df_with_cat1[['model_label', 'probability', 'is_equal']] = df_with_cat1[
            ['product_name', 'category_1']].apply(
            lambda x: product_name_clf.predict(*x),
            axis=1,
            result_type="expand")

    df = pd.concat([df_with_cat1, df_without_cat1])

    df.loc[
        ((df["probability"] > 0.70) & (~df['is_equal'])), 'light'] = 3  # Красный - модель уверена, что ввели не то
    # Пользователь не поставил метку, но модель уверена
    # Пользователь поставил метку, они совпали
    # ---
    df.loc[
        ((df["probability"] > 0.70) & (df['is_equal'])), 'light'] = 1  # Зеленый
    df.loc[(df['light'].isnull()), 'light'] = 2  # Желтый

    return df


def get_subcategory_info(request, *args, **kwargs):
    # Category.objects.filter(~Q(sub_code__contains='.0'), code=kwargs['category_id'], removed=False)
    subcategory_list = Category.objects.filter(code=kwargs['category_id'], removed=False)
    return JsonResponse({'category_id': kwargs['category_id'], 'subcategories': list(subcategory_list.values())})


def single_check(request, *args, **kwargs):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            inputProductName = data.get('inputProductName')
            inputCategoryId = data.get('inputCategoryId')
            inputSubcategoryId = data.get('inputSubcategoryId').rsplit(r'.', 1)[-1]
            # product_name_clf = ProductNameClassifier()

            result = {}
            print(inputProductName, inputCategoryId)
            if inputCategoryId.isdigit() and Category.objects.filter(code=inputCategoryId).exists():
                if inputSubcategoryId.isdigit() and Category.objects.filter(code=inputCategoryId,
                                                                            sub_code=inputSubcategoryId).exists():
                    # Все параметры известны, пробуем предсказать
                    pass
                else:
                    label, probability, is_equal = product_name_clf.predict(inputProductName, int(inputCategoryId))
                    result['label_category_id'] = label
                    category = Category.objects.filter(code=label).distinct().first()
                    result['label_category_text'] = category.text
                    result["probability"] = probability
                    result["is_equal"] = is_equal
            else:
                # Когда известно только название
                label, probability = product_name_clf.predict(inputProductName)
                result['label_category_id'] = label
                print(label)
                category = Category.objects.filter(code=label).distinct().first()
                if not category:
                    raise Exception("Необходимо задать категорию!")
                result['label_category_text'] = category.text
                result["probability"] = probability

            if result["probability"] > 0.70:
                if result.get('is_equal', None) != False:
                    result['light'] = 3  # Зеленый
                else:
                    result['light'] = 1  # Красный
            else:
                result['light'] = 2  # Желтый

            # df.loc[((df["probability"] > 0.70) & (~df['is_equal'])), 'light'] = 1  # Зеленый
            # # Пользователь не поставил метку, но модель уверена
            # # Пользователь поставил метку, они совпали
            # # ---
            # df.loc[((df["probability"] > 0.70) & (df['is_equal'])), 'light'] = 3  # Красный - модель уверена, что ввели не то
            # df.loc[(df['light'].isnull()), 'light'] = 2  # Желтый

            print(data)
            return JsonResponse({'status': 'ok', "result": result})
        except Exception as e:
            # raise e
            return JsonResponse({'status': 'error', 'detail': str(e)})
