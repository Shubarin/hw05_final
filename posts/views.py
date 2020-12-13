from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import (get_list_or_404, get_object_or_404, redirect,
                              render)
from django.urls import reverse
from django.views.decorators.cache import cache_page
from yatube.settings import RECORDS_ON_THE_PAGE

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


@cache_page(20)
def index(request):
    posts = Post.objects.all()
    paginator = Paginator(posts, RECORDS_ON_THE_PAGE)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    context = {
        "paginator": paginator,
        "page": page
    }
    return render(request, "index.html", context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)

    posts = group.posts.all()
    paginator = Paginator(posts, RECORDS_ON_THE_PAGE)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    context = {
        "paginator": paginator,
        "group": group,
        "page": page
    }
    return render(request, "group.html", context)


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(reverse("posts:index"))

    return render(request, "new_post.html", {"form": form})


def profile(request, username):
    user = get_object_or_404(User.objects, username=username)
    posts = user.posts.all()
    user_post_count = user.posts.all().count()
    paginator = Paginator(posts, RECORDS_ON_THE_PAGE)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    context = {
        "paginator": paginator,
        "profile_user": user,
        "user_post_count": user_post_count,
        "page": page,
    }
    return render(request, "profile.html", context)


def post_view(request, username, post_id):
    post = get_object_or_404(Post.objects, id=post_id,
                             author__username=username)
    user = post.author
    comments = post.comments.all()
    user_post_count = Post.objects.filter(author=user).count()
    form = CommentForm(request.POST or None)
    context = {
        "profile_user": user,
        "user_post_count": user_post_count,
        "post": post,
        "form": form,
        "comments": comments
    }

    return render(request, "post.html", context)


def post_edit(request, username, post_id):
    current_user = request.user
    post = get_object_or_404(Post.objects, id=post_id,
                             author__username=username)
    post_author_user = post.author
    if current_user != post_author_user:
        return redirect("posts:index")

    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if form.is_valid():
        form.save()
        return redirect(reverse("posts:post", kwargs={"username": username,
                                                      "post_id": post_id}))

    return render(request, "new_post.html", {"form": form,
                                             "action_text": 'Редактировать',
                                             "post": post})


@login_required
def add_comment(request, username, post_id):
    form = CommentForm(request.POST or None)
    post = Post.objects.get(id__exact=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect(reverse("posts:post", kwargs={'username': username,
                                                      'post_id': post.id}))

    return render(request, "comments.html", {"form": form,
                                             "post": post})


def page_not_found(request, exception=None):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def follow_index(request):
    user = request.user
    posts = Post.objects.filter(author__following__user=user)
    paginator = Paginator(posts, RECORDS_ON_THE_PAGE)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    context = {
        "paginator": paginator,
        "page": page,
        "profile_user": user,
    }
    return render(request, "follow.html", context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User.objects, username=username)
    if user != author:
        Follow.objects.get_or_create(
            user=user,
            author=author,
        )
    return redirect(reverse("posts:profile", kwargs={"username": username}))


@login_required
def profile_unfollow(request, username):
    follow = get_object_or_404(Follow, author__username=username, user=request.user)
    follow.delete()
    return redirect(reverse("posts:profile", kwargs={"username": username}))
