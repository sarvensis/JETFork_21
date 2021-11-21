from django.contrib import admin
from .models import *


# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ('code', 'text', 'removed',)
#     list_filter = ('code', 'text', 'removed',)


# @admin.register(Subcategory)
# class SubcategoryAdmin(admin.ModelAdmin):
#     list_display = ('category_id', 'code', 'text', 'removed',)
#     list_filter = ('category_id', 'code', 'text', 'removed',)

@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ('email', 'ipaddress', 'datetime',)
    list_filter = ('email', 'ipaddress', 'datetime',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_model_label', )
    list_filter = ('status', 'category_model_label',)


