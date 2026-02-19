import logging

import aiohttp

from app.db.session import async_session_factory
from app.db.content_item_get import get_content_item_by_id
from app.db.log_error import save_error_log
from app.agents.qa_agent import analyze_article, analyze_image_generation

logger = logging.getLogger(__name__)

# =========================
# VK Конфигурация
# =========================
VK_ACCESS_TOKEN = "YOUR_VK_ACCESS_TOKEN"
VK_GROUP_ID = "YOUR_VK_GROUP_ID"  # числовой ID группы, без минуса


# =========================
# Async task
# =========================
async def publish_vk_task(content_item_id: int) -> None:
    """
    Публикует статью + изображения в VK группу.
    """

    async with async_session_factory() as session:
        try:
            # 1. Получаем контент
            content_item = await get_content_item_by_id(
                session=session,
                content_item_id=content_item_id,
            )

            if not content_item:
                await save_error_log(
                    session=session,
                    module="publish_vk_task",
                    entity_id=content_item_id,
                    error="Content item not found",
                    severity="high",
                    cause="Invalid content_item_id",
                    recommendation="Check DB and content pipeline",
                )
                await session.commit()
                return

            if not content_item.text:
                raise RuntimeError("Article text is empty, cannot publish")

            # 2. QA проверки перед публикацией
            qa_article = await analyze_article(
                title=content_item.title,
                article_text=content_item.text,
            )

            if qa_article["score"] < 5:
                raise RuntimeError(
                    f"Article failed QA (score={qa_article['score']})"
                )

            if content_item.images:
                qa_images = await analyze_image_generation(
                    title=content_item.title,
                    images=content_item.images,
                )
                if qa_images["score"] < 5:
                    raise RuntimeError(
                        f"Images failed QA (score={qa_images['score']})"
                    )

            # 3. Публикация текста
            post_payload = {
                "owner_id": f"-{VK_GROUP_ID}",
                "from_group": 1,
                "message": f"{content_item.title}\n\n{content_item.text}",
                "access_token": VK_ACCESS_TOKEN,
                "v": "5.131",
            }

            async with aiohttp.ClientSession() as session_http:
                async with session_http.post(
                    "https://api.vk.com/method/wall.post",
                    params=post_payload,
                ) as resp:
                    resp_data = await resp.json()
                    if "error" in resp_data:
                        raise RuntimeError(
                            f"VK wall.post error: {resp_data['error']}"
                        )

                    post_id = resp_data["response"]["post_id"]

            # 4. Публикация изображений (если есть)
            if content_item.images:
                async with aiohttp.ClientSession() as session_http:
                    for img_url in content_item.images:
                        # Получаем upload_url
                        params = {
                            "group_id": VK_GROUP_ID,
                            "access_token": VK_ACCESS_TOKEN,
                            "v": "5.131",
                        }
                        async with session_http.get(
                            "https://api.vk.com/method/photos.getWallUploadServer",
                            params=params,
                        ) as resp:
                            upload_resp = await resp.json()
                            if "error" in upload_resp:
                                raise RuntimeError(
                                    f"VK upload server error: {upload_resp['error']}"
                                )
                            upload_url = upload_resp["response"]["upload_url"]

                        # Загружаем фото на сервер VK
                        async with session_http.post(
                            upload_url, data={"photo": img_url}
                        ) as upload_result:
                            upload_data = await upload_result.json()

                        # Сохраняем фото на стене
                        save_params = {
                            "group_id": VK_GROUP_ID,
                            "server": upload_data["server"],
                            "photo": upload_data["photo"],
                            "hash": upload_data["hash"],
                            "access_token": VK_ACCESS_TOKEN,
                            "v": "5.131",
                        }
                        async with session_http.post(
                            "https://api.vk.com/method/photos.saveWallPhoto",
                            params=save_params,
                        ) as save_resp:
                            save_data = await save_resp.json()
                            if "error" in save_data:
                                raise RuntimeError(
                                    f"VK saveWallPhoto error: {save_data['error']}"
                                )

                        photo_id = save_data["response"][0]["id"]

                        # Привязываем к посту
                        attach_params = {
                            "owner_id": f"-{VK_GROUP_ID}",
                            "post_id": post_id,
                            "attachments": f"photo-{VK_GROUP_ID}_{photo_id}",
                            "access_token": VK_ACCESS_TOKEN,
                            "v": "5.131",
                        }
                        async with session_http.post(
                            "https://api.vk.com/method/wall.edit",
                            params=attach_params,
                        ) as edit_resp:
                            edit_data = await edit_resp.json()
                            if "error" in edit_data:
                                raise RuntimeError(
                                    f"VK wall.edit error: {edit_data['error']}"
                                )

            logger.info(
                "Content item %s published to VK", content_item_id
            )

        except Exception as e:
            logger.exception(
                "Error publishing content_item_id=%s to VK", content_item_id
            )

            await save_error_log(
                session=session,
                module="publish_vk_task",
                entity_id=content_item_id,
                error=str(e),
                severity="high",
                cause=None,
                recommendation="Check VK token, group ID, content quality",
            )
            await session.commit()
