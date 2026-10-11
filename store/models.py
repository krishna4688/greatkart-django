from django.db import models
from category.models import Category
from django.urls import reverse

# Create your models here.
class Product(models.Model):
    product_name = models.CharField(max_length=50 , unique=True)
    slug         = models.SlugField(max_length=50 , unique=True)
    description  = models.TextField(max_length=200 , blank=True)
    price        = models.DecimalField(max_digits=10, decimal_places=2)
    image        = models.ImageField(upload_to='photo/products')
    stock        = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True) 
    category     = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)


    def get_url(self):
        return reverse('product_detail' , args=[self.category.slug, self.slug])


    def __str__(self):
        return self.product_name