"""
Product Database URL configuration (namespace "productdb")
"""
from django.conf.urls import include, url
from django.views.generic.base import RedirectView
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.serializers import AuthTokenSerializer

from app.productdb import api_views
from app.productdb import views
from rest_framework import routers, status
from rest_framework.authtoken import views as authtoken_views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

import app.productdb.datatables as datatables

router = routers.DefaultRouter()
router.register(r'vendors', api_views.VendorViewSet, basename="vendors")
router.register(r'products', api_views.ProductViewSet, basename="products")
router.register(r'productgroups', api_views.ProductGroupViewSet, basename="productgroups")
router.register(r'productlists', api_views.ProductListViewSet, basename="productlists")
router.register(r'productmigrationsources', api_views.ProductMigrationSourceViewSet, basename="productmigrationsources")
router.register(r'productmigrationoptions', api_views.ProductMigrationOptionViewSet, basename="productmigrationoptions")
router.register(r'notificationmessages', api_views.NotificationMessageViewSet, basename="notificationmessages")
router.register(r'productidnormalizationrules', api_views.ProductIdNormalizationRuleViewSet, basename="productidnormalizationrules")

schema_view = get_schema_view(
   openapi.Info(
      title="Product Database API",
      default_version="v1",
      description="REST API specification for the product database",
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

decorated_login_view = \
    swagger_auto_schema(
        method="post",
        tags=["Token authentication"],
        operation_id="login_token",
        operation_description="obtain a token for login",
        request_body=AuthTokenSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "token": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="authentication token"
                        )
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                "login failed"
            )
        }
    )(authtoken_views.obtain_auth_token)

decorated_logout_view = \
    swagger_auto_schema(
        method="post",
        tags=["Token authentication"],
        operation_description="logout session and/or invalidate token for user",
        operation_id="logout_token",
        responses={
            status.HTTP_200_OK: openapi.Response(
                "logout successful"
            )
        }
    )(api_views.TokenLogoutApiView.as_view())

# namespace: productdb
urlpatterns = [
    # API related URLs
    url(r'^api-docs(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name="api-schema-json"),
    url(r'^api-docs/$', schema_view.with_ui('swagger', cache_timeout=0), name="apidocs"),
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/token-auth/', decorated_login_view, name="api-token-auth"),
    url(r'^api/token-logout/', decorated_logout_view, name="api-token-logout"),
    url(r'^api/$', RedirectView.as_view(url="v1/", permanent=False), name="api_redirect"),

    # Datatables endpoints
    url(
        r'^datatables/vendor_products/(?P<vendor_id>[0-9]+)/$',
        datatables.VendorProductListJson.as_view(),
        name='datatables_vendor_products_endpoint'
    ),
    url(
        r'^datatables/vendor_products/$',
        datatables.VendorProductListJson.as_view(),
        name='datatables_vendor_products_view'
    ),
    url(
        r'^datatables/product_data/$',
        datatables.ListProductsJson.as_view(),
        name='datatables_list_products_view'
    ),
    url(
        r'^datatables/product_groups_data/$',
        datatables.ListProductGroupsJson.as_view(),
        name='datatables_list_product_groups'
    ),
    url(
        r'^datatables/product_groups_data/(?P<product_group_id>[0-9]+)/products/$',
        datatables.ListProductsByGroupJson.as_view(),
        name='datatables_list_products_by_group_view'
    ),

    # user views
    url(r'^vendor/$', views.browse_vendor_products, name='browse_vendor_products'),

    url(r'^productgroups/$', views.list_product_groups, name='list-product_groups'),
    url(r'^productgroup/$', views.detail_product_group, name='detail-product_group'),
    url(r'^productgroup/(?P<product_group_id>\d+)/$', views.detail_product_group, name='detail-product_group'),

    url(r'^productlists/$', views.list_product_lists, name='list-product_lists'),
    url(r'^productlist/$', views.detail_product_list, name='detail-product_list'),
    url(r'^productlist/(?P<product_list_id>\d+)/$', views.detail_product_list, name='detail-product_list'),
    url(r'^productlist/add', views.add_product_list, name="add-product_list"),
    url(r'^productlist/edit/$', views.edit_product_list, name='edit-product_list'),
    url(r'^productlist/edit/(?P<product_list_id>\d+)/$', views.edit_product_list, name='edit-product_list'),
    url(r'^productlist/delete/$', views.delete_product_list, name='delete-product_list'),
    url(r'^productlist/delete/(?P<product_list_id>\d+)/$', views.delete_product_list, name='delete-product_list'),

    url(r'^share/productlist/(?P<product_list_id>\d+)/$', views.share_product_list, name='share-product_list'),

    url(r'^productcheck/(?P<product_check_id>\d+)/$', views.detail_product_check, name="detail-product_check"),
    url(r'^productcheck/create/$', views.create_product_check, name="create-product_check"),
    url(r'^productcheck/$', views.list_product_checks, name="list-product_checks"),

    url(r'^products/$', views.browse_all_products, name='all_products'),
    url(r'^product/$', views.view_product_details, name='product-list'),
    url(r'^product/(?P<product_id>\d+)/$', views.view_product_details, name='product-detail'),

    url(r'^profile/edit/$', views.edit_user_profile, name='edit-user_profile'),

    url(r'^import/products/$', views.import_products, name='import_products'),
    url(r'^import/productmigrations/$', views.import_product_migrations, name='import_product_migrations'),
    url(r'^about/$', views.about_view, name='about'),
    url(r'^$', views.home, name='home'),
]

app_name = "productdb"
