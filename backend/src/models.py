from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, TEXT, Date
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.schema import CheckConstraint
import datetime

Base = declarative_base()

class Artist(Base):
    __tablename__ = 'artists'
    artist_id = Column(TEXT, primary_key=True)
    name = Column(TEXT, nullable=False)
    spotify_url = Column(TEXT)
    image_url = Column(TEXT)
    genres = Column(ARRAY(TEXT))

    albums = relationship("Album", back_populates="primary_artist")
    listens = relationship("Listen", back_populates="artist")

class Album(Base):
    __tablename__ = 'albums'
    album_id = Column(TEXT, primary_key=True)
    name = Column(TEXT, nullable=False)
    release_date = Column(Date)
    album_type = Column(TEXT)
    spotify_url = Column(TEXT)
    image_url = Column(TEXT)
    primary_artist_id = Column(TEXT, ForeignKey('artists.artist_id'))

    primary_artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album")
    listens = relationship("Listen", back_populates="album")

class Track(Base):
    __tablename__ = 'tracks'
    track_id = Column(TEXT, primary_key=True)
    name = Column(TEXT, nullable=False)
    duration_ms = Column(Integer)
    explicit = Column(Boolean)
    popularity = Column(Integer)
    preview_url = Column(TEXT)
    spotify_url = Column(TEXT)
    album_id = Column(TEXT, ForeignKey('albums.album_id'))
    available_markets = Column(ARRAY(TEXT))
    last_played_at = Column(DateTime(timezone=True))

    album = relationship("Album", back_populates="tracks")
    listens = relationship("Listen", back_populates="track")

class Listen(Base):
    __tablename__ = 'listens'
    listen_id = Column(Integer, primary_key=True, autoincrement=True)
    played_at = Column(DateTime(timezone=True), nullable=False, unique=True)
    item_type = Column(TEXT, nullable=False)
    track_id = Column(TEXT, ForeignKey('tracks.track_id'), nullable=True)
    episode_id = Column(TEXT, nullable=True)
    artist_id = Column(TEXT, ForeignKey('artists.artist_id'), nullable=True)
    album_id = Column(TEXT, ForeignKey('albums.album_id'), nullable=True)

    track = relationship("Track", back_populates="listens")
    artist = relationship("Artist", back_populates="listens")
    album = relationship("Album", back_populates="listens")

    __table_args__ = (
        CheckConstraint(
            "(item_type = 'track' AND track_id IS NOT NULL AND episode_id IS NULL) OR (item_type = 'episode' AND episode_id IS NOT NULL AND track_id IS NULL)",
            name='ck_listen_item_type'
        ),
    )

class RecentlyPlayedTracksRaw(Base):
    __tablename__ = 'recently_played_tracks_raw'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(JSONB, nullable=False)
    ingestion_timestamp = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
