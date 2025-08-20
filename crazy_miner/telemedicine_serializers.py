from rest_framework import serializers

from django.conf import settings
from .models import Visit, Transaction, CustomUser, Comment, Blog, BoxMoney

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
        """
        Validate an uploaded drug image and ensure it does not exceed the configured maximum size.
        
        If a file is provided, delegates to validate_image_size which will raise a serializers.ValidationError when the file size exceeds MAX_UPLOAD_SIZE. Returns the original value unchanged.
        """
        if value:
            self.validate_image_size(value)

        return value

    def validate_image_size(self, value):
        """
        Validate that an uploaded file does not exceed settings.MAX_UPLOAD_SIZE.
        
        If the file-like `value` has a `.size` greater than settings.MAX_UPLOAD_SIZE, raises
        serializers.ValidationError with a Persian message indicating the maximum allowed size.
        `value` is expected to be an UploadedFile-like object (e.g., an ImageField file).
        """
        if value.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f'حجم فایل نمی‌تواند بیشتر از {settings.MAX_UPLOAD_SIZE / 1048576:.1f} مگابایت باشد.'
            )





    def create(self, validated_data):
        """
        Create and return a Visit instance after assigning the currently authenticated request user.
        
        This injects the authenticated user from self.context['request'].user into validated_data['user'] before delegating creation to the superclass.
        
        Parameters:
            validated_data (dict): Serializer-validated data for the Visit; the 'user' key will be set.
        
        Returns:
            Visit: The newly created Visit model instance.
        """
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
