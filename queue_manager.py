"""队列管理模块 - 管理兑换码生成任务队列"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from newapi_service import NewAPIService
from config import settings


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待中
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


@dataclass
class RedeemTask:
    """兑换码生成任务"""

    task_id: str
    user_id: int
    username: str
    quota: int
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None  # 生成的兑换码
    error: Optional[str] = None  # 错误信息


class QueueManager:
    """队列管理器"""

    def __init__(self, max_concurrent: int = 1):
        """
        初始化队列管理器

        Args:
            max_concurrent: 最大并发数（默认为1，按顺序处理）
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, RedeemTask] = {}  # 所有任务
        self.queue: asyncio.Queue = asyncio.Queue()  # 任务队列
        self.processing_count = 0  # 当前处理中的任务数
        self._worker_started = False
        self._workers: list = []

    async def start_workers(self):
        """启动工作进程"""
        if self._worker_started:
            return

        self._worker_started = True
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop_workers(self):
        """停止工作进程"""
        self._worker_started = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    async def add_task(
        self,
        user_id: int,
        username: str,
        quota: int = 500000,
    ) -> str:
        """
        添加任务到队列

        Args:
            user_id: 用户ID
            username: 用户名
            quota: 额度

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = RedeemTask(
            task_id=task_id,
            user_id=user_id,
            username=username,
            quota=quota,
        )

        self.tasks[task_id] = task
        await self.queue.put(task_id)

        return task_id

    async def get_task(self, task_id: str) -> Optional[RedeemTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    async def get_user_tasks(self, user_id: int) -> list[RedeemTask]:
        """获取用户的所有任务"""
        return [task for task in self.tasks.values() if task.user_id == user_id]

    async def _worker(self, worker_id: int):
        """工作进程"""
        print(f"队列工作进程 {worker_id} 启动")

        while self._worker_started:
            try:
                # 从队列获取任务
                task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                task = self.tasks.get(task_id)

                if not task:
                    continue

                # 处理任务
                await self._process_task(task)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"工作进程 {worker_id} 发生错误: {e}")

        print(f"队列工作进程 {worker_id} 停止")

    async def _process_task(self, task: RedeemTask):
        """处理任务"""
        print(f"开始处理任务 {task.task_id} - 用户: {task.username}")

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        self.processing_count += 1

        try:
            # 检查 New API 配置
            if not settings.newapi_site_url or not settings.newapi_access_token:
                raise Exception("New API 未配置")

            # 创建 New API 服务
            newapi_service = NewAPIService(
                base_url=settings.newapi_site_url,
                access_token=settings.newapi_access_token,
                api_user=settings.newapi_user,
            )

            # 调用 New API 创建兑换码
            result = await newapi_service.create_redemption_code(
                quota=task.quota,
                count=1,
                name=f"用户 {task.username} 每日兑换码",
            )

            # 提取兑换码
            if not result or "data" not in result:
                raise Exception("返回数据格式错误")

            codes = result.get("data", [])
            if not codes or len(codes) == 0:
                raise Exception("未返回兑换码")

            code = codes[0] if isinstance(codes, list) else str(codes)

            # 标记任务完成
            task.status = TaskStatus.COMPLETED
            task.result = code
            task.completed_at = datetime.now()

            print(f"任务 {task.task_id} 处理完成 - 兑换码: {code}")

        except Exception as e:
            # 标记任务失败
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()

            print(f"任务 {task.task_id} 处理失败: {e}")

        finally:
            self.processing_count -= 1

    def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        pending_count = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.PENDING
        )
        processing_count = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.PROCESSING
        )
        completed_count = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED
        )
        failed_count = sum(
            1 for task in self.tasks.values() if task.status == TaskStatus.FAILED
        )

        return {
            "total_tasks": len(self.tasks),
            "pending": pending_count,
            "processing": processing_count,
            "completed": completed_count,
            "failed": failed_count,
            "queue_size": self.queue.qsize(),
            "max_concurrent": self.max_concurrent,
        }


# 全局队列管理器实例
queue_manager = QueueManager(max_concurrent=1)
