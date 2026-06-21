import pytest

from onboard.app import OnboardApp


@pytest.mark.asyncio
async def test_wizard_boots_to_welcome():
    app = OnboardApp()
    async with app.run_test() as pilot:
        # App title carries the brand; the welcome screen is on top of the stack.
        assert "Alien-Trade" in app.title
        assert app.screen_stack[-1].__class__.__name__ == "WelcomeScreen"
        await pilot.pause()


@pytest.mark.asyncio
async def test_advances_off_welcome():
    app = OnboardApp()
    async with app.run_test() as pilot:
        await pilot.press("enter")          # Start → next screen
        await pilot.pause()
        assert app.screen_stack[-1].__class__.__name__ != "WelcomeScreen"
