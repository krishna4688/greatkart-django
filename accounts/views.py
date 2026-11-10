from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages,auth
from django.contrib.auth.decorators import login_required

from django.views.decorators.csrf import ensure_csrf_cookie

#VERIFICATION EMAIL
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

from django.utils.encoding import force_str

from cart.views import _cart_id
from cart.models import CartItem,Cart

import requests

@ensure_csrf_cookie
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email,password=password)
            user.phone_number = phone_number
            user.save()


            #USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string(
                    'accounts/account_verification_email.html',{
                    'user': user,
                    'domain': current_site,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                    })
            to_email = email
            send_email = EmailMessage(
                mail_subject,
                message,
                to=[to_email] )
            send_email.send()
            
            # messages.success(request,'Registration successful.')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
      form = RegistrationForm()  

    context = {
    'form':form,
    }
    return render(request, 'accounts/register.html',context)


def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Get guest cart before login
        old_cart_id = _cart_id(request)

        try:
            guest_cart = Cart.objects.get(cart_id=old_cart_id)
            guest_cart_items = list(
                CartItem.objects.filter(cart=guest_cart)
            )

        except Cart.DoesNotExist:
            guest_cart = None
            guest_cart_items = []

        # Authenticate user
        user = auth.authenticate(email=email, password=password)

        if user is not None:

            # Login user
            auth.login(request, user)

            # Merge guest cart with user's existing cart
            if guest_cart:

                for guest_item in guest_cart_items:

                    guest_variations = set(
                        guest_item.variation.values_list('id', flat=True)
                    )

                    user_cart_items = CartItem.objects.filter(
                        user=user,
                        product=guest_item.product
                    ).exclude(id=guest_item.id)

                    matching_item = None

                    for existing_item in user_cart_items:

                        existing_variations = set(
                            existing_item.variation.values_list('id', flat=True)
                        )

                        if guest_variations == existing_variations:
                            matching_item = existing_item
                            break

                    if matching_item:
                        matching_item.quantity += guest_item.quantity
                        matching_item.save()
                        guest_item.delete()

                    else:
                        guest_item.user = user
                        guest_item.save()

                # Update cart session ID
                guest_cart.cart_id = _cart_id(request)
                guest_cart.save()

            messages.success(request, 'You are now logged in.')

            # Redirect to previous page using requests
            try:
                url = request.META.get('HTTP_REFERER')
                query = requests.utils.urlparse(url).query
                params = dict(
                    x.split('=') for x in query.split('&')
                )

                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)

            except (TypeError, ValueError, AttributeError):
                pass

            return redirect('dashboard')

        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'you are logged out.')
    return redirect('login')



def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)

    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        

        messages.success(request, 'Your account is activated successfully.')
        return redirect('login')

    else:
        messages.error(request, 'Invalid activation link.')
        return redirect('register')
   
@login_required(login_url = 'login')
def dashboard(request):
    return render(request,'accounts/dashboard.html')

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            # email password request

            current_site = get_current_site(request)
            mail_subject = 'Reset your password'
            message = render_to_string(
            'accounts/reset_password_email.html',{
            'user': user,
            'domain': current_site,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(
                 mail_subject,
                 message,
                 to=[to_email] )
            send_email.send()

            messages.success(request, 'Password reset email has sent to your email address')
            return redirect('login')

        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgotPassword')
       
    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request,uidb64,token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request , 'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request,'This link has been expired!')
        return redirect('login')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request,'Password reset successfull')
            return redirect('login')

        else:
            messages.error(request, 'Password do not match!')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')


   