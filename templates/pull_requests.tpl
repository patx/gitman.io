% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " pull requests", user=user, error=error, notice=notice)

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <div class="panel-heading">
    <h2>Pull requests</h2>
    <div class="filters">
      <a class="{{'active' if status == 'open' else ''}}" href="?status=open">Open ({{counts["open"]}})</a>
      <a class="{{'active' if status == 'merged' else ''}}" href="?status=merged">Merged ({{counts["merged"]}})</a>
      <a class="{{'active' if status == 'closed' else ''}}" href="?status=closed">Closed ({{counts["closed"]}})</a>
      <a class="{{'active' if status == 'all' else ''}}" href="?status=all">All</a>
      % if user:
        <a href="/{{repo['owner_username']}}/{{repo['name']}}/pulls/new">New pull request</a>
      % else:
        <a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/pulls/new">New pull request</a>
      % end
    </div>
  </div>
  % if pull_requests:
    <ul class="issue-list">
      % for pr in pull_requests:
        <li>
          <a href="/{{repo['owner_username']}}/{{repo['name']}}/pulls/{{pr['number']}}">#{{pr["number"]}} {{pr["title"]}}</a>
          <span>({{pr["status"]}} from {{pr["source_owner_username"]}}/{{pr["source_repo_name"]}} {{format_ref_label(pr["source_ref_type"], pr["source_ref_name"])}} into {{format_ref_label(pr["target_ref_type"], pr["target_ref_name"])}})</span>
        </li>
      % end
    </ul>
  % else:
    <p class="empty">No {{status}} pull requests.</p>
  % end
</section>
