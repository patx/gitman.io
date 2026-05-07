<div class="repo-title-row">
  <h1><a href="/{{repo['owner_username']}}">{{repo["owner_username"]}}</a>/{{repo["name"]}}</h1>
  % include("ref_selector.tpl", repo=repo)
</div>
% if get("repo_indexing", False):
  <p class="muted">Repository metadata is indexing. Counts and ref lists may update shortly.</p>
% end
