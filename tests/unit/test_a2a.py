import pytest

from eco_sentinel.a2a.protocol import A2ABus, A2ARequest, AgentCard


@pytest.mark.asyncio
async def test_a2a_call_ok():
    bus = A2ABus(timeout_s=2)

    async def handler(req: A2ARequest):
        return {"echo": req.payload}

    bus.register(AgentCard("test", "Test", "test", ["echo"]), handler)
    req = A2ARequest(target="test", capability="echo", payload={"x": 1})
    resp = await bus.call(req)
    assert resp.status == "ok"
    assert resp.result["echo"] == {"x": 1}


@pytest.mark.asyncio
async def test_a2a_unknown():
    bus = A2ABus()
    resp = await bus.call(A2ARequest(target="unknown", capability="x"))
    assert resp.status == "error"


@pytest.mark.asyncio
async def test_a2a_timeout():
    bus = A2ABus(timeout_s=0.05)

    async def slow(req: A2ARequest):
        import asyncio

        await asyncio.sleep(1)
        return {}

    bus.register(AgentCard("slow", "Slow", "slow", ["slow"]), slow)
    resp = await bus.call(A2ARequest(target="slow", capability="slow"))
    assert resp.status == "timeout"
