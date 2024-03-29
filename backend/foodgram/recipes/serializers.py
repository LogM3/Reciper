from django.db.transaction import atomic
from rest_framework.serializers import (CurrentUserDefault, DictField,
                                        HiddenField, ListField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField, ReadOnlyField,
                                        SerializerMethodField, ValidationError)

from tags.models import Tag
from tags.serializers import TagSerializer
from users.models import User
from users.serializers import READ_ONLY_USER_FIELDS, CustomUserSerializer
from .fields import Base64ImageField
from .models import Cart, Ingredient, IngredientRecipe, Recipe, RecipeFollow
from .utils import add_ingredients

RECIPE_FIELDS = (
    'id',
    'tags',
    'author',
    'ingredients',
    'name',
    'image',
    'text',
    'cooking_time',
    'is_favorited',
    'is_in_shopping_cart'
)
RECIPE_CREATE_CUTOFF_INDEX = -2


class IngredientsSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsRecipeSerializer(ModelSerializer):
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(source='ingredient.measurement_unit')
    id = ReadOnlyField(source='ingredient.id')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class ReadOnlyRecipeSerializer(ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer(many=False, read_only=True)
    ingredients = IngredientsRecipeSerializer(
        many=True, source='ingredientrecipe_set'
    )
    is_favorited = SerializerMethodField()
    is_in_shopping_cart = SerializerMethodField()

    class Meta:
        model = Recipe
        fields = RECIPE_FIELDS

    def get_is_favorited(self, obj):
        user = self.context.get('request').user

        if user.is_anonymous:
            return False
        return RecipeFollow.objects.filter(
            recipe=obj,
            user=user
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user

        if user.is_anonymous:
            return False
        return Cart.objects.filter(
            recipe=obj,
            user=user
        ).exists()


class ShortRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class CreateRecipeSerializer(ModelSerializer):
    tags = PrimaryKeyRelatedField(many=True, queryset=Tag.objects.all())
    author = HiddenField(default=CurrentUserDefault())
    ingredients = ListField(child=DictField(), write_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = RECIPE_FIELDS[:RECIPE_CREATE_CUTOFF_INDEX]

    def validate_ingredients(self, ingredients_data):
        ingredients_ids = set()

        for ingredient in ingredients_data:
            keys = ingredient.keys()
            if 'id' not in keys or 'amount' not in keys:
                raise ValidationError('Invalid ingredient data')

            ingredient_id = ingredient.get('id')
            if ingredient.get('id') in ingredients_ids:
                raise ValidationError(
                    f'Duplicate ingredient ID: {ingredient_id}')
            ingredients_ids.add(ingredient_id)

            if not Ingredient.objects.filter(id=ingredient_id).exists():
                raise ValidationError('No such ingredient')
            if int(ingredient.get('amount')) < 1:
                raise ValidationError('Amount must be greater or equal 1')

        return ingredients_data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        return add_ingredients(ingredients_data, recipe)

    def update(self, instance, validated_data):
        instance.tags.set(validated_data.get('tags'))
        with atomic():
            instance.ingredientrecipe_set.all().delete()
            return add_ingredients(
                validated_data.get('ingredients'),
                instance
            )

    def to_representation(self, instance):
        return ReadOnlyRecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class CustomUserSerializerWithRecipes(CustomUserSerializer):
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = User
        fields = READ_ONLY_USER_FIELDS

    def get_recipes(self, obj):
        limit = self.context.get('request').GET.get('recipes_limit')
        if limit:
            return ShortRecipeSerializer(
                Recipe.objects.filter(author=obj)[:int(limit)],
                many=True
            ).data
        return ShortRecipeSerializer(
            Recipe.objects.filter(author=obj),
            many=True
        ).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
