from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import audited

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .throttles import ClientIpScopedThrottle, LoginFailureGuard, is_trusted_device, mark_trusted_device


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Sets the csrftoken cookie. The frontend calls this once on load."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


# DRF only checks CSRF for already-authenticated sessions; login and register
# are protected explicitly so a third-party site cannot log a victim in.
@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "register"
    throttle_classes = [ClientIpScopedThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "login"
    throttle_classes = [ClientIpScopedThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        guard = LoginFailureGuard(
            email, ClientIpScopedThrottle().get_ident(request), trusted_device=is_trusted_device(request, email)
        )
        guard.reserve_attempt()
        user = authenticate(request, email=email, password=serializer.validated_data["password"])
        if user is None:
            # Same message for unknown email and wrong password: no account enumeration.
            raise AuthenticationFailed("Invalid email or password.", code="invalid_credentials")
        guard.release_after_success()
        login(request, user)  # rotates the session key (prevents session fixation)
        response = Response(UserSerializer(user).data)
        mark_trusted_device(response, user)
        return response


class LogoutView(APIView):
    def post(self, request):
        logout(request)  # deletes the server-side session (ADR 0001)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with audited(request.user, request.user):
            serializer.save()
        return Response(serializer.data)
