% profile_name = profile_user["display_name"] or profile_user["username"]
% rebase("base.tpl", title=profile_name, user=user, error=error, notice=notice)

<section class="profile-header">
  <h1>{{profile_name}}</h1>
  % if profile_user["display_name"]:
    <p class="muted">@{{profile_user["username"]}}</p>
  % end
  % if profile_user["bio"]:
    <p>{{!render_markdown_links(profile_user["bio"])}}</p>
  % else:
    <p class="empty">No bio yet.</p>
  % end
  % if profile_user["website"]:
    <p><a href="{{profile_user['website']}}" rel="nofollow">{{profile_user["website"]}}</a></p>
  % end
  <p class="muted"><small>
    Joined {{profile_user["created_at"]}}
    % if is_self:
      <a class="button-link" href="/settings/profile">Edit profile</a>
    % end
  </small></p>
</section>

<section class="panel">
  <div class="panel-heading">
    <h2>Repositories</h2>
    <nav class="tabs">
      <a class="{{'active' if active_tab == 'owned' else ''}}" href="/{{profile_user['username']}}">Owned ({{len(owned_repos)}})</a>
      <a class="{{'active' if active_tab == 'stars' else ''}}" href="/{{profile_user['username']}}?tab=stars">Starred ({{len(starred_repos)}})</a>
    </nav>
  </div>
  % if repos:
      % for repo in repos:
        <a href="/{{repo['owner_username']}}/{{repo['name']}}">
          <strong>{{repo["owner_username"]}}/{{repo["name"]}}</strong></a>
          <br>
          {{!render_markdown_links(repo["description"]) or "No description yet."}}
          <br>
          <small>Updated {{repo["updated_at"]}} · {{repo["star_count"]}} stars</small>
          <br>
          <br>
      % end
  % else:
    <p class="empty">{{"No starred repositories yet." if active_tab == "stars" else "No repositories yet."}}</p>
  % end
</section>
