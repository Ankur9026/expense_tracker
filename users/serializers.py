from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user



class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class ChangePasswordSerializer(serializers.Serializer):

    old_password = serializers.CharField(write_only=True)

    new_password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    def validate_old_password(self, value):
        user = self.context['request'].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Old password is incorrect."
            )

        return value

    def validate_new_password(self, value):
        try:
            validate_password(
                value,
                user=self.context['request'].user
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)

        return value
    

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
            token.blacklist()
        except Exception:
            raise serializers.ValidationError(
                "Invalid or expired refresh token."
            )

        return value