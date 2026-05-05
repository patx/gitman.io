% source_repo = get("source_repo", None)
% if source_repo:
  <p class="eyebrow">Fork of <a href="/{{source_repo['owner_username']}}/{{source_repo['name']}}">{{source_repo["owner_username"]}}/{{source_repo["name"]}}</a>.</p>
% end
