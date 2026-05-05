% active_tab = get("repo_active_tab", "")
% selected_ref = get("selected_ref", None)
<nav class="repo-tabs">
  <a class="repo-tab {{'active' if active_tab == 'overview' else ''}}" href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'], selected_ref)}}">Overview</a>
  <a class="repo-tab {{'active' if active_tab == 'source' else ''}}" href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/src', selected_ref)}}">Source</a>
  <a class="repo-tab {{'active' if active_tab == 'commits' else ''}}" href="{{url_with_ref('/' + repo['owner_username'] + '/' + repo['name'] + '/commits', selected_ref)}}">Commits{{" (" + str(commit_count) + ")" if commit_count else ""}}</a>
  <a class="repo-tab {{'active' if active_tab == 'issues' else ''}}" href="/{{repo['owner_username']}}/{{repo['name']}}/issues">Issues{{" (" + str(issue_counts["open"]) + ")" if issue_counts["open"] else ""}}</a>
  <a class="repo-tab {{'active' if active_tab == 'pulls' else ''}}" href="/{{repo['owner_username']}}/{{repo['name']}}/pulls">Pull requests{{" (" + str(pr_counts["open"]) + ")" if pr_counts["open"] else ""}}</a>
  % if user:
    <form class="inline-form" method="post" action="/{{repo['owner_username']}}/{{repo['name']}}/star">
      {{!csrf_field()}}
      % if is_starred:
        <input type="hidden" name="action" value="unstar">
        <button class="button-link" type="submit">Unstar ({{star_count}})</button>
      % else:
        <input type="hidden" name="action" value="star">
        <button class="button-link" type="submit">Star ({{star_count}})</button>
      % end
    </form>
  % else:
    <a class="button-link" href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}">Star ({{star_count}})</a>
  % end
  % if user and not is_owner and not has_fork:
    <form class="inline-form" method="post" action="/{{repo['owner_username']}}/{{repo['name']}}/fork">
      {{!csrf_field()}}
      <input type="hidden" name="name" value="{{repo['name']}}">
      <input type="hidden" name="description" value="{{repo['description']}}">
      <button class="button-link" type="submit">Fork</button>
    </form>
  % elif not user:
    <a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/fork">Fork</a>
  % end
  % if is_owner:
    <a class="repo-tab {{'active' if active_tab == 'settings' else ''}}" href="/{{repo['owner_username']}}/{{repo['name']}}/settings">Settings</a>
  % end
</nav>
