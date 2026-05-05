% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " issues", user=user, error=error, notice=notice)

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
      <a class="{{'active' if status == 'open' else ''}}" href="?status=open">Open ({{counts["open"]}})</a>
      <a class="{{'active' if status == 'closed' else ''}}" href="?status=closed">Closed ({{counts["closed"]}})</a>
      <a class="{{'active' if status == 'all' else ''}}" href="?status=all">All</a>
      % if user:
        <a href="/{{repo['owner_username']}}/{{repo['name']}}/issues/new">New issue</a>
      % else:
        <a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/issues/new">New issue</a>
      % end
    </div>
  </div>
  % if issues:
    <ul class="issue-list">
      % for issue in issues:
        <li>
          <a href="/{{repo['owner_username']}}/{{repo['name']}}/issues/{{issue['number']}}">#{{issue["number"]}} {{issue["title"]}}</a> <span>({{issue["status"]}})</span>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No {{status}} issues.</p>
  % end
</section>
