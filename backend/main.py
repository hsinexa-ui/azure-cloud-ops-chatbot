import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ChatRequest, ChatResponse, OperationResponse, StopRequest
from .services.vm_service import VMService, VMServiceError


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


# =========================================================
# VM SERVICE
# =========================================================

vm_service = VMService(settings)

pending_stop = False


# =========================================================
# APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Azure VM Chatbot started | environment=%s | vm=%s",
        settings.environment,
        settings.vm_name or "not configured",
    )

    yield

    logger.info("Azure VM Chatbot stopped")


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Azure VM Control Chatbot",
    description="Chatbot API for checking, starting and stopping an Azure VM.",
    version="1.0.0",
    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Azure VM Control Chatbot",
        "status": "running",
        "environment": settings.environment,
        "vm_name": settings.vm_name,
        "docs": "/docs",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# VM STATUS
# =========================================================

@app.get(
    "/vm/status",
    response_model=OperationResponse,
)
def get_vm_status():

    try:
        status = vm_service.get_vm_status()

        return OperationResponse(
            success=True,
            message=status,
            vm_name=settings.vm_name,
            status=status,
        )

    except VMServiceError as exc:

        logger.error(
            "VM status failed | category=%s",
            exc.category,
        )

        return OperationResponse(
            success=False,
            message=str(exc),
            vm_name=settings.vm_name,
        )


# =========================================================
# START VM
# =========================================================

@app.post(
    "/vm/start",
    response_model=OperationResponse,
)
def start_vm():

    try:
        message = vm_service.start_vm()

        return OperationResponse(
            success=True,
            message=message,
            vm_name=settings.vm_name,
        )

    except VMServiceError as exc:

        logger.error(
            "VM start failed | category=%s",
            exc.category,
        )

        return OperationResponse(
            success=False,
            message=str(exc),
            vm_name=settings.vm_name,
        )


# =========================================================
# STOP VM
# =========================================================

@app.post(
    "/vm/stop",
    response_model=OperationResponse,
)
def stop_vm(request: StopRequest):

    if not request.confirmed:

        return OperationResponse(
            success=False,
            requires_confirmation=True,
            message="Please confirm that you want to stop the VM.",
            vm_name=settings.vm_name,
        )

    try:

        message = vm_service.stop_vm()

        return OperationResponse(
            success=True,
            message=message,
            vm_name=settings.vm_name,
        )

    except VMServiceError as exc:

        logger.error(
            "VM stop failed | category=%s",
            exc.category,
        )

        return OperationResponse(
            success=False,
            message=str(exc),
            vm_name=settings.vm_name,
        )


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_message(message: str) -> str:

    return re.sub(
        r"[^a-z0-9 ]",
        "",
        message.lower(),
    ).strip()


# =========================================================
# CONFIRMATION
# =========================================================

def is_confirmation(message: str) -> bool:

    return normalize_message(message) in {
        "yes",
        "y",
        "confirm",
        "confirmed",
    }


# =========================================================
# CANCELLATION
# =========================================================

def is_cancellation(message: str) -> bool:

    return normalize_message(message) in {
        "no",
        "n",
        "cancel",
        "cancelled",
    }


# =========================================================
# STATUS COMMAND
# =========================================================

def looks_like_status(message: str) -> bool:

    text = normalize_message(message)

    return (
        "status" in text
        or "is the vm running" in text
        or "is my vm running" in text
        or "vm status" in text
    )


# =========================================================
# START COMMAND
# =========================================================

def looks_like_start(message: str) -> bool:

    text = normalize_message(message)

    return (
        ("start" in text and "vm" in text)
        or ("start" in text and "dev" in text)
        or ("turn on" in text and "vm" in text)
        or ("turn on" in text and "dev" in text)
    )


# =========================================================
# STOP COMMAND
# =========================================================

def looks_like_stop(message: str) -> bool:

    text = normalize_message(message)

    return (
        ("stop" in text and "vm" in text)
        or ("stop" in text and "dev" in text)
        or ("turn off" in text and "vm" in text)
        or ("turn off" in text and "dev" in text)
    )


# =========================================================
# CHATBOT
# =========================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    global pending_stop

    message = request.message

    # =====================================================
    # STOP CONFIRMATION
    # =====================================================

    if pending_stop:

        if request.confirmed is not None:
            confirmation = request.confirmed
        else:
            confirmation = is_confirmation(message)

        # -------------------------------------------------
        # USER CONFIRMED
        # -------------------------------------------------

        if confirmation:

            pending_stop = False

            try:

                result = vm_service.stop_vm()

                return ChatResponse(
                    success=True,
                    reply=result,
                    action="stop",
                    vm_name=settings.vm_name,
                )

            except VMServiceError as exc:

                logger.error(
                    "VM stop failed | category=%s",
                    exc.category,
                )

                return ChatResponse(
                    success=False,
                    reply=str(exc),
                    action="stop",
                    vm_name=settings.vm_name,
                )

        # -------------------------------------------------
        # USER CANCELLED
        # -------------------------------------------------

        if (
            is_cancellation(message)
            or request.confirmed is False
        ):

            pending_stop = False

            return ChatResponse(
                success=True,
                reply="Stop cancelled. The VM was not changed.",
                action="cancel",
            )

        # -------------------------------------------------
        # WAIT FOR YES / NO
        # -------------------------------------------------

        return ChatResponse(
            success=False,
            reply="Please reply with 'yes' to stop the VM or 'no' to cancel.",
            action="stop",
            requires_confirmation=True,
            vm_name=settings.vm_name,
        )

    # =====================================================
    # STATUS
    # =====================================================

    if looks_like_status(message):

        try:

            status = vm_service.get_vm_status()

            return ChatResponse(
                success=True,
                reply=status,
                action="status",
                vm_name=settings.vm_name,
                status=status,
            )

        except VMServiceError as exc:

            return ChatResponse(
                success=False,
                reply=str(exc),
                action="status",
                vm_name=settings.vm_name,
            )

    # =====================================================
    # START
    # =====================================================

    if looks_like_start(message):

        try:

            result = vm_service.start_vm()

            return ChatResponse(
                success=True,
                reply=result,
                action="start",
                vm_name=settings.vm_name,
            )

        except VMServiceError as exc:

            return ChatResponse(
                success=False,
                reply=str(exc),
                action="start",
                vm_name=settings.vm_name,
            )

    # =====================================================
    # STOP
    # =====================================================

    if looks_like_stop(message):

        pending_stop = True

        return ChatResponse(
            success=True,
            reply=(
                f"You are about to stop {settings.vm_name}. "
                "This is a potentially disruptive operation. "
                "Do you want to continue?"
            ),
            action="stop",
            requires_confirmation=True,
            vm_name=settings.vm_name,
        )

    # =====================================================
    # UNKNOWN COMMAND
    # =====================================================

    return ChatResponse(
        success=False,
        reply=(
            "I can check VM status, start the configured DEV VM, "
            "or stop the VM after confirmation."
        ),
    )