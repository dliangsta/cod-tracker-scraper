import json
import os

from selenium import webdriver


N_ROWS = 10000
USER = "SRX"
# USER = "Buffasian0912"
USER_TO_URL = {
  "SRX": "https://cod.tracker.gg/warzone/profile/battlenet/dliangsta%231633/matches",
  "Buffasian0912": "https://cod.tracker.gg/warzone/profile/xbl/YEEH%20IM%20ASIAN/matches",
}
REQUIRED_TEAM = [
  "SRX",
  "Buffasian0912",
]
URL = USER_TO_URL[USER]
STATS_FN = f"{USER}/stats.json"
LINKS_FN = f"{USER}/links.json"


def get_last_matches(driver, num):
  assert num > 0
  driver.get(URL)
  match_rows = []
  counts = []
  while len(match_rows) < num:
    print(len(match_rows))
    driver.find_element_by_xpath("//button[text()[contains(.,'Load More Matches')]]").click()
    matches = driver.find_element_by_class_name("trn-gamereport-list")
    match_rows = matches.find_elements_by_class_name("match__row")
    counts.append(len(match_rows))
    if len(counts) > 10 and all(c == counts[-1] for c in counts[-10:]):
      break
  print(len(match_rows))
  if num > len(match_rows):
    match_rows = match_rows[:num]
  return match_rows


def get_links(match_rows, links):
  for match_row in match_rows:
    link = match_row.find_element_by_class_name("match__link").get_attribute("href")
    if link not in links:
      links.append(link)
  write_links(links)
  return links


def get_damage_stats_from_link(driver, link):
  driver.get(link)
  damage_stats = {}
  for team in driver.find_elements_by_class_name("team__players"):
    if USER not in team.get_attribute('innerHTML'):
      continue

    for player in team.find_elements_by_class_name("player"):
      player_name = player.find_element_by_class_name("player__name").text
      player_name = player_name[player_name.find("\n"):].strip()
      stats_panel = player.find_element_by_class_name("player__info-stats")
      damage_panel = stats_panel.find_elements_by_class_name("numbers")[1]
      damage = int(damage_panel.find_element_by_class_name("value").text.replace(",", ""))
      damage_stats[player_name] = damage

    team_damage = sum(damage for player, damage in damage_stats.items() if player != USER)
    return damage_stats, damage_stats[USER], team_damage
  raise Exception("Bad!")


def get_damage_stats_from_links(driver, links, stats):
  for i, link in enumerate(links):
    if link not in stats:
      try:
        stats[link], my_damage, team_damage = get_damage_stats_from_link(driver, link)
        more_than_team_combined, most, total = count_stats(stats, links)
        print(
          f"{i+1:3d}/{len(links)}: ({my_damage:5d}, {team_damage:5d}). "
          f"Count: ({more_than_team_combined:3d}/{most:3d}/{total:3d}) ({link})"
        )
        write_stats(stats)
      except Exception as e:
        print(e)
  return stats


def write_stats(stats):
  with open(STATS_FN, "w") as f:
    json.dump(stats, f, indent=2)


def read_stats():
  if not os.path.isfile(STATS_FN):
    write_stats({})
  with open(STATS_FN) as f:
    return json.load(f)


def write_links(links):
  with open(LINKS_FN, "w") as f:
    json.dump(links, f, indent=2)


def read_links():
  if not os.path.isfile(LINKS_FN):
    write_links([])
  with open(LINKS_FN) as f:
    return json.load(f)


def has_most_damage(damage_stats):
  return damage_stats[USER] > sum(damage for player, damage in damage_stats.items() if player != USER)


def count_stats(stats, links):
  more_than_team_combined, most, total = 0, 0, 0
  for link, damage_stats in stats.items():
    if link not in links:
      continue
    my_damage = damage_stats[USER]
    team_damage = sum(damage for player, damage in damage_stats.items() if player != USER)
    if not team_damage + my_damage:
      continue
    if not all(required_team_member in damage_stats for required_team_member in REQUIRED_TEAM):
      continue
    if has_most_damage(damage_stats):
      more_than_team_combined += 1
    if my_damage == max(damage_stats.values()):
      most += 1
    total += 1

  return more_than_team_combined, most, total


def main():
  if not os.path.exists(USER):
    os.makedirs(USER)

  driver = webdriver.Chrome(executable_path="/usr/local/bin/chromedriver")
  driver.implicitly_wait(30)

  stats = read_stats()
  links = read_links()

  match_rows = get_last_matches(driver, N_ROWS)

  links = get_links(match_rows, links)

  if len(links) > N_ROWS:
    links = links[:N_ROWS]

  try:
    stats = get_damage_stats_from_links(driver, links, stats)
  except KeyboardInterrupt:
    print("Keyboard interrupt. Stopping.")


  more_than_team_combined, most, total = count_stats(stats, links)

  print(
    f"Of the {total} games (all that we could get from CodTracker) that SRX "
    f"and Buffasian0912 have played together, there have been "
    f"{more_than_team_combined} ({more_than_team_combined / total * 100:.3f}%) "
    f"games where {USER}'s damage has been greater than the rest of the teams "
    f"combined and {most} games ({most / total * 100:3f}%) where {USER}'s "
    f"damage has been the highest on the team."
  )


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
  main()

