from rest_framework import serializers

from django.conf import settings
from .telemedicin_models import (
    Visit, Transaction, CustomUser, Comment, Blog, BoxMoney,
    CrazyMinerPayment, CrazyMinerPaymentLog
)

MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE
class CustomUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email']


class CustomUserProfileJustUserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username']


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['phone_number', 'auth_code']


class VisitSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    drug_images = serializers.ImageField(
        max_length=None,
        allow_empty_file=False,
        use_url=True,
        required=False
    )

    class Meta:
        model = Visit
        fields = [
            'id',
            'user',
            'name',
            'urgency',
            'general_symptoms',
            'neurological_symptoms',
            'cardiovascular_symptoms',
            'gastrointestinal_symptoms',
            'respiratory_symptoms',
            'description',
            'created_at',
            'drug_images'
        ]

    def validate_drug_images(self, value):
        if value:
            self.validate_image_size(value)

        return value

    def validate_image_size(self, value):
        if value.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f'حجم فایل نمی‌تواند بیشتر از {settings.MAX_UPLOAD_SIZE / 1048576:.1f} مگابایت باشد.'
            )





    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'user', 'trans_id', 'amount', 'status', 'created_at', 'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    blog = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'comment', 'likes', 'blog', 'created_at']


class BlogSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Blog
        fields = ['id', 'title', 'content', 'author', 'image1', 'image2', 'created_at', 'comments']


class BoxMoneySerializer(serializers.ModelSerializer):
    class Meta:
        model = BoxMoney
        fields = '__all__'


# CrazyMiner Payment Serializers
class CrazyMinerCreatePaymentSerializer(serializers.Serializer):
    """سریالایزر برای ایجاد درخواست شارژ کیف پول"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    description = serializers.CharField(required=False, allow_blank=True, default="شارژ کیف پول")
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("مبلغ باید بیشتر از صفر باشد")
        if value < 10000:  # حداقل 10,000 ریال
            raise serializers.ValidationError("حداقل مبلغ شارژ 10,000 ریال است")
        return value


class CrazyMinerPaymentCallbackSerializer(serializers.Serializer):
    """سریالایزر برای callback درگاه پرداخت"""
    trans_id = serializers.CharField()
    id_get = serializers.CharField()
    
    # فیلدهای اختیاری که ممکن است از درگاه بیاید
    amount = serializers.DecimalField(max_digits=10, decimal_places=0, required=False)
    status = serializers.CharField(required=False)
    tracking_code = serializers.CharField(required=False)


class CrazyMinerPaymentSerializer(serializers.ModelSerializer):
    """سریالایزر برای مدل CrazyMinerPayment"""
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CrazyMinerPayment
        fields = [
            'id', 'user', 'user_phone', 'amount', 'status', 'status_display',
            'gateway_transaction_id', 'gateway_reference_id', 'gateway_tracking_code',
            'description', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'gateway_transaction_id', 
            'gateway_reference_id', 'gateway_tracking_code',
            'created_at', 'updated_at', 'completed_at'
        ]


class CrazyMinerPaymentStatusSerializer(serializers.Serializer):
    """سریالایزر برای پاسخ وضعیت پرداخت"""
    transaction_id = serializers.UUIDField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    gateway_tracking_code = serializers.CharField(required=False)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(required=False)
    payment_url = serializers.URLField(required=False)


class CrazyMinerPaymentLogSerializer(serializers.ModelSerializer):
    """سریالایزر برای مدل CrazyMinerPaymentLog"""
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    
    class Meta:
        model = CrazyMinerPaymentLog
        fields = ['id', 'payment', 'log_type', 'log_type_display', 'message', 'raw_data', 'created_at']
        read_only_fields = ['id', 'created_at']
