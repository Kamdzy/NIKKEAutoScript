from module.base.timer import Timer
from module.liberation.assets import *
from module.ui.assets import GOTO_BACK, TEAM_GOTO_LIBERATION
from module.ui.page import page_team
from module.ui.ui import UI


class Liberation(UI):
    # Kamdzy - claim a "✓ Complete" pill using LUMA template matching.
    #
    # Each Daily Proxy Volunteer row is colour-coded by its point tier
    # (10P/20P/30P) and the tiers reshuffle between rows every day. An RGB
    # template captured from one tier therefore scores by pill colour rather
    # than by the button's text: a teal "✓ Complete" capture matched a cyan
    # "➜ Go" pill at 0.898 (clicking "Go" navigated out to the Enhance
    # Equipment screen), while a genuinely claimable gold "✓ Complete" only
    # reached 0.797 and was skipped. No threshold separates those.
    #
    # Matching the white glyphs on the Y channel removes the tier colour from
    # the comparison. Measured on one live screen (gold Complete / cyan Go /
    # purple Complete): 1.000 / 0.330 / 0.926.
    def claim_completed(self, button, interval=1, similarity=0.85):
        name = f'{button.name}_luma'
        if name in self.interval_timer:
            if self.interval_timer[name].limit != interval:
                self.interval_timer[name] = Timer(interval)
        else:
            self.interval_timer[name] = Timer(interval)
        if not self.interval_timer[name].reached():
            return False

        self.device.stuck_record_add(button)
        if not button.match_luma(self.device.image, offset=(5, 5), similarity=similarity):
            return False

        self.interval_timer[name].reset()
        self.device.click(button)
        return True

    def _run(self, skip_first_screenshot=True):
        confirm_timer = Timer(10, count=10).start()
        click_timer = Timer(0.3)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if click_timer.reached() and self.appear_then_click(TEAM_GOTO_LIBERATION, offset=(30, 30), interval=2):
                confirm_timer.reset()
                click_timer.reset()
                continue

            # Kamdzy - the three visible rows are claimed via luma matching, see
            # claim_completed above. COMPLETED_4..6 keep the upstream RGB path:
            # their en-US templates were never recaptured, so they simply do not
            # match here and must not be given a colour-blind matcher that could
            # start firing on the wrong pills.
            if click_timer.reached() and self.claim_completed(COMPLETED_1):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.claim_completed(COMPLETED_2):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.claim_completed(COMPLETED_3):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.appear_then_click(
                COMPLETED_4, offset=(30, 30), interval=1, threshold=0.8, static=False
            ):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.appear_then_click(
                COMPLETED_5, offset=(30, 30), interval=1, threshold=0.8, static=False
            ):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.appear_then_click(
                COMPLETED_6, offset=(30, 30), interval=1, threshold=0.8, static=False
            ):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if click_timer.reached() and self.appear_then_click(
                CONFIRM_D, offset=(30, 30), interval=1, threshold=0.8, static=False
            ):
                self.config.modified['Liberation.Scheduler.Enable'] = False
                confirm_timer.reset()
                click_timer.reset()
                continue

            # if click_timer.reached() and self.handle_event(1):
            #     confirm_timer.reset()
            #     click_timer.reset()
            #     continue

            if click_timer.reached() and self.handle_reward(1):
                confirm_timer.reset()
                click_timer.reset()
                continue

            if self.appear(GOTO_BACK, offset=(30, 30)) and confirm_timer.reached():
                break

    def run(self):
        self.ui_ensure(page_team, skip_first_screenshot=True)
        self._run()
        self.config.task_delay(schedule=True)
