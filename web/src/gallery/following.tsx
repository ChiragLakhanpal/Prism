// The gallery's Following page (ticket 37): the status badges with Not checked, the signal lines with the Strong
// signal tag, the Following list in its states, the track record, the follow control in each state and the mission
// brief's parts. The list and the brief are the server's answers on the fixture (tests/record_following_api.py); the
// states the fixture cannot reach are the following-made-up-*.json answers, made up from the real one and saying so.
import real from "../../../tests/fixtures/api/following-p156634.json";
import madeUpStates from "../../../tests/fixtures/api/following-made-up-states.json";
import manyQuiet from "../../../tests/fixtures/api/following-made-up-many-quiet.json";
import allQuiet from "../../../tests/fixtures/api/following-made-up-all-quiet.json";
import tracked from "../../../tests/fixtures/api/following-made-up-track-record.json";
import brief from "../../../tests/fixtures/api/drafts-mission-brief-draft.json";
import type { ReactNode } from "react";
import { FollowControl } from "../components/FollowControl";
import { Tag } from "../components/LessonParts";
import { MissionBriefParts } from "../components/MissionBriefParts";
import { StatusBadge } from "../components/StatusBadge";
import { copy } from "../copy";
import type { Draft } from "../lib/drafts";
import type { Following } from "../lib/following";
import { FollowingBody, FollowingSkeleton } from "../pages/FollowingPage";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.followingStates;
const B = brief as unknown as Draft;
const numbers = new Map(B.sources.map((source) => [source.evidence_id, source.number]));
const PID = B.subject.project_id;

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

export function followingPage(): GalleryPage {
  return {
    slug: "following",
    current: "projects",
    wide: true,
    sections: [
      {
        id: "badges",
        title: t.badges,
        body: (
          <div className="flex flex-wrap items-center gap-4">
            <StatusBadge kind="needs-a-look" />
            <StatusBadge kind="watch" />
            <StatusBadge kind="no-signals" />
            <StatusBadge kind="not-checked" />
            <Tag>{copy.following.strongTag}</Tag>
          </div>
        ),
      },
      { id: "populated", title: t.populated, body: <FollowingBody data={real as unknown as Following} /> },
      { id: "states", title: t.states, body: <FollowingBody data={madeUpStates as unknown as Following} /> },
      { id: "many-quiet", title: t.manyQuiet, body: <FollowingBody data={manyQuiet as unknown as Following} /> },
      { id: "all-quiet", title: t.allQuiet, body: <FollowingBody data={allQuiet as unknown as Following} /> },
      { id: "track", title: t.track, body: <FollowingBody data={tracked as unknown as Following} /> },
      { id: "loading", title: t.loading, body: <FollowingSkeleton /> },
      {
        id: "follow",
        title: t.follow,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={t.followOff}>
              <FollowControl pid={PID} name={null} sample={{ following: false }} />
            </Labeled>
            <Labeled label={t.followSaving}>
              <FollowControl pid={PID} name={null} sample={{ following: false, busy: true }} />
            </Labeled>
            <Labeled label={t.followOn}>
              <FollowControl pid={PID} name={null} sample={{ following: true }} />
            </Labeled>
            <Labeled label={t.followFailed}>
              <FollowControl pid={PID} name={null} sample={{ following: false, failed: true }} />
            </Labeled>
            <Labeled label={t.followLoading}>
              <FollowControl pid={PID} name={null} sample={{ following: null }} />
            </Labeled>
          </div>
        ),
      },
      {
        id: "brief",
        title: t.brief,
        body: (
          <div className="@container/doc max-w-[46.5rem]">
            <MissionBriefParts notes={B.notes} evidence={B.evidence} numbers={numbers} opened={new Set()} open={{ id: null, sentence: null }} subject={B.subject} />
          </div>
        ),
      },
    ],
  };
}
