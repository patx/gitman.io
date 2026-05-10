% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " issues", user=user, error=error, notice=notice)
% q = get("q", "")
% issue_scope = "issues" if status == "all" else status + " issues"

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <div class="panel-heading">
    <h2>Issues</h2>
    <div class="filters">
      <a class="{{'active' if status == 'open' else ''}}" href="{{current_url_with_params(status='open')}}">Open ({{counts["open"]}})</a>
      <a class="{{'active' if status == 'closed' else ''}}" href="{{current_url_with_params(status='closed')}}">Closed ({{counts["closed"]}})</a>
      <a class="{{'active' if status == 'all' else ''}}" href="{{current_url_with_params(status='all')}}">All</a>
      <form class="list-search" action="/{{repo['owner_username']}}/{{repo['name']}}/issues" method="get" role="search">
        <input type="hidden" name="status" value="{{status}}">
        <label class="sr-only" for="issue-search-input">Search issues</label>
        <input id="issue-search-input" type="search" name="q" value="{{q}}" placeholder="Search issues" autocomplete="off">
        <button type="submit">Search</button>
        % if q:
          <a href="{{current_url_with_params(q=None)}}">Clear</a>
        % end
      </form>
      % if user:
        <a href="/{{repo['owner_username']}}/{{repo['name']}}/issues/new">New issue</a>
      % else:
        <a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/issues/new">New issue</a>
      % end
    </div>
  </div>
  % if issues:
    <ul class="issue-list" data-paginated-list>
      % for issue in issues:
        <li>
          <a href="/{{repo['owner_username']}}/{{repo['name']}}/issues/{{issue['number']}}">#{{issue["number"]}} {{issue["title"]}}</a> <span>({{issue["status"]}})</span>
        </li>
      % end
    </ul>
    % include("pagination.tpl", pagination=pagination)
  % else:
    % if q:
      <p class="empty">No {{issue_scope}} matching "{{q}}".</p>
    % else:
      <p class="empty">No {{issue_scope}}.</p>
    % end
    % include("pagination.tpl", pagination=pagination)
  % end
</section>
