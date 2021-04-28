import uvicorn

from loguru import logger

from .__version__ import __version__


def main():
    logger.info(f"monipy v{__version__}")

    uvicorn.run(
        "monipy.app:app",
        host="0.0.0.0",
        port=8080,
        log_level="warning",
        reload=False,
    )


if __name__ == "__main__":
    main()
